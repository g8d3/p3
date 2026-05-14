package main

import (
	"embed"
	"fmt"
	"io/fs"
	"log"
	"math/rand"
	"net/http"
	"os"
	"path/filepath"
	"time"
)

//go:embed web/*
var webFS embed.FS

func main() {
	dataDir := "."
	if len(os.Args) > 1 {
		dataDir = os.Args[1]
	}

	absDir, err := filepath.Abs(dataDir)
	if err != nil {
		fmt.Printf("[csv-tabulator] Error: %v\n", err)
		os.Exit(1)
	}

	info, err := os.Stat(absDir)
	if err != nil || !info.IsDir() {
		fmt.Printf("[csv-tabulator] Error: '%s' no es un directorio válido\n", absDir)
		os.Exit(1)
	}

	state := NewAppState(absDir)
	state.loadActions()

	fmt.Printf("[csv-tabulator] Directorio de datos: %s\n", absDir)
	fmt.Printf("[csv-tabulator] Servidor iniciado en: http://localhost:8080\n")

	mux := http.NewServeMux()

	// API routes
	mux.HandleFunc("GET /api/data", state.handleGetData)
	mux.HandleFunc("GET /api/info", state.handleGetInfo)
	mux.HandleFunc("POST /api/cell", state.handleUpdateCell)
	mux.HandleFunc("POST /api/row", state.handleRowOp)
	mux.HandleFunc("POST /api/column", state.handleColumnOp)
	mux.HandleFunc("POST /api/file", state.handleFileOp)
	mux.HandleFunc("POST /api/save", state.handleSave)
	mux.HandleFunc("POST /api/action/execute", state.handleExecuteAction)
	mux.HandleFunc("GET /api/files", state.handleListFiles)
	mux.HandleFunc("GET /api/actions", state.handleListActions)
	mux.HandleFunc("POST /api/actions", state.handleCreateAction)
	mux.HandleFunc("PUT /api/actions/{id}", state.handleUpdateAction)
	mux.HandleFunc("DELETE /api/actions/{id}", state.handleDeleteAction)

	// Frontend (embedded)
	webSubFS, err := fs.Sub(webFS, "web")
	if err != nil {
		log.Fatal(err)
	}
	fileServer := http.FileServer(http.FS(webSubFS))
	mux.Handle("GET /", fileServer)

	// Wrap with logging middleware
	handler := loggingMiddleware(mux)

	log.Fatal(http.ListenAndServe(":8080", handler))
}

// ═══════════════════════════════════════════════════════════════
// LOGGING MIDDLEWARE — registra TODAS las requests
// ═══════════════════════════════════════════════════════════════

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()

		// Wrap ResponseWriter to capture status code
		lrw := &loggingResponseWriter{ResponseWriter: w, statusCode: 200}
		next.ServeHTTP(lrw, r)

		duration := time.Since(start)
		path := r.URL.Path
		if r.URL.RawQuery != "" {
			path += "?" + r.URL.RawQuery
		}

		// Read request body for POST (up to 2KB for logging)
		var bodyPreview string
		if r.Method == "POST" && lrw.bodyBytes > 0 {
			bodyPreview = fmt.Sprintf(" (%d bytes body)", lrw.bodyBytes)
		}

		fmt.Fprintf(os.Stderr, "[%s] %s %s → %d %s%s\n",
			start.Format("15:04:05.000"),
			r.Method, path,
			lrw.statusCode, duration.Round(time.Millisecond),
			bodyPreview,
		)

		// Log errors more prominently
		if lrw.statusCode >= 400 {
			fmt.Fprintf(os.Stderr, "  ⚠️  ERROR %d en %s %s\n", lrw.statusCode, r.Method, path)
		}
	})
}

type loggingResponseWriter struct {
	http.ResponseWriter
	statusCode int
	bodyBytes  int64
}

func (lrw *loggingResponseWriter) WriteHeader(code int) {
	lrw.statusCode = code
	lrw.ResponseWriter.WriteHeader(code)
}

func (lrw *loggingResponseWriter) Write(b []byte) (int, error) {
	lrw.bodyBytes += int64(len(b))
	return lrw.ResponseWriter.Write(b)
}

// ── Utility ──────────────────────────────────────────────────────

func randID() string {
	const chars = "abcdefghijklmnopqrstuvwxyz0123456789"
	b := make([]byte, 8)
	for i := range b {
		b[i] = chars[rand.Intn(len(chars))]
	}
	return string(b)
}
