package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"sync"
	"time"
)

// ─── Runtime config (mutable via API) ────────────────────────────────────

type RuntimeConfig struct {
	mu           sync.RWMutex
	APIKey       string `json:"api_key,omitempty"`
	BaseURL      string `json:"base_url"`
	Model        string `json:"model"`
	SystemPrompt string `json:"system_prompt"`
	MaxIter      int    `json:"max_iter"`
}

var rcfg *RuntimeConfig

func initConfig() {
	rcfg = &RuntimeConfig{
		APIKey:       os.Getenv("OPENCODE_GO_API_KEY"),
		BaseURL:      strings.TrimRight(os.Getenv("OPENCODE_GO_BASE_URL"), "/"),
		Model:        os.Getenv("OPENCODE_GO_MODEL"),
		SystemPrompt: defaultPrompt,
		MaxIter:      3,
	}
	// try loading system prompt from file if env not set and no inline prompt
	if os.Getenv("OPENCODE_GO_SYSTEM_PROMPT") != "" {
		rcfg.SystemPrompt = os.Getenv("OPENCODE_GO_SYSTEM_PROMPT")
	} else if os.Getenv("OPENCODE_GO_SYSTEM_PROMPT_FILE") != "" {
		b, err := os.ReadFile(os.Getenv("OPENCODE_GO_SYSTEM_PROMPT_FILE"))
		if err != nil {
			log.Printf("WARN: failed to read system prompt file %s: %v", os.Getenv("OPENCODE_GO_SYSTEM_PROMPT_FILE"), err)
		} else {
			rcfg.SystemPrompt = string(b)
		}
	}
}

func (c *RuntimeConfig) Get() (string, string, string, string, int) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.APIKey, c.BaseURL, c.Model, c.SystemPrompt, c.MaxIter
}

func (c *RuntimeConfig) Set(apiKey, baseURL, model, systemPrompt string, maxIter int) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if apiKey != "" {
		c.APIKey = apiKey
	}
	if baseURL != "" {
		c.BaseURL = baseURL
	}
	if model != "" {
		c.Model = model
	}
	if systemPrompt != "" {
		c.SystemPrompt = systemPrompt
	}
	if maxIter > 0 {
		c.MaxIter = maxIter
	}
}

const defaultPrompt = `You are an AI assistant that can execute shell commands. Rules:

1. Greetings, chit-chat, explanations → plain text. No tags.

2. To get filesystem or system info → <cmd>command</cmd>. I will run it and give you the real output.

3. After each command result, decide: if you have the answer, wrap it in <done>your answer</done> and stop. If you need more info, run ONE more <cmd>.

4. NEVER repeat a command you already ran. Check the conversation history first.

5. <done> ends the conversation. Use it as soon as you can answer the user.`

// ─── OpenAI-compatible API types ─────────────────────────────────────────

type Message struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

type ChatRequest struct {
	Model    string    `json:"model"`
	Messages []Message `json:"messages"`
}

type ChatChoice struct {
	Message Message `json:"message"`
}

type ChatResponse struct {
	Choices []ChatChoice `json:"choices"`
}

// ─── Sessions ────────────────────────────────────────────────────────────

type Session struct {
	ID        string    `json:"id"`
	Messages  []Message `json:"-"`
	CreatedAt time.Time `json:"created_at"`
}

var (
	sessions   = map[string]*Session{}
	sessionsMu sync.RWMutex
)

func newSessionID() string {
	b := make([]byte, 8)
	if _, err := rand.Read(b); err != nil {
		log.Fatalf("rand.Read: %v", err)
	}
	return hex.EncodeToString(b)
}

func getSession(id string) *Session {
	sessionsMu.RLock()
	defer sessionsMu.RUnlock()
	return sessions[id]
}

func createSession() *Session {
	id := newSessionID()
	s := &Session{
		ID:        id,
		Messages:  []Message{},
		CreatedAt: time.Now(),
	}
	sessionsMu.Lock()
	sessions[id] = s
	sessionsMu.Unlock()
	return s
}

// ─── Tag parsing ─────────────────────────────────────────────────────────

func parseTag(s, tag string) (string, bool) {
	open := "<" + tag + ">"
	close := "</" + tag + ">"
	i := strings.Index(s, open)
	if i < 0 {
		return "", false
	}
	j := strings.Index(s[i+len(open):], close)
	if j < 0 {
		return "", false
	}
	return s[i+len(open) : i+len(open)+j], true
}

func stripTags(s string) string {
	s = strings.ReplaceAll(s, "<cmd>", "")
	s = strings.ReplaceAll(s, "</cmd>", "")
	s = strings.ReplaceAll(s, "<done>", "")
	s = strings.ReplaceAll(s, "</done>", "")
	return strings.TrimSpace(s)
}

// ─── API client ──────────────────────────────────────────────────────────

var httpClient = &http.Client{Timeout: 30 * time.Second}

func callAI(apiKey, baseURL, model string, msgs []Message) (string, error) {
	body := ChatRequest{
		Model:    model,
		Messages: msgs,
	}
	b, err := json.Marshal(body)
	if err != nil {
		return "", fmt.Errorf("json marshal: %w", err)
	}

	url := strings.TrimRight(baseURL, "/") + "/chat/completions"
	req, err := http.NewRequest("POST", url, bytes.NewReader(b))
	if err != nil {
		return "", fmt.Errorf("new request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("http call: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("read body: %w", err)
	}
	if resp.StatusCode != 200 {
		errBody := string(raw)
		if len(errBody) > 500 {
			errBody = errBody[:500]
		}
		return "", fmt.Errorf("API %d: %s", resp.StatusCode, errBody)
	}

	var cr ChatResponse
	if err := json.Unmarshal(raw, &cr); err != nil {
		return "", fmt.Errorf("json unmarshal: %w", err)
	}
	if len(cr.Choices) == 0 {
		return "", fmt.Errorf("API returned 0 choices")
	}
	return cr.Choices[0].Message.Content, nil
}

// ─── Command executor ────────────────────────────────────────────────────

var cwd string

func runCmd(cmdStr string) (string, error) {
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	defer cancel()

	sh := exec.CommandContext(ctx, "sh", "-c", cmdStr)
	sh.Dir = cwd

	var outb, errb bytes.Buffer
	sh.Stdout = &outb
	sh.Stderr = &errb

	exitCode := 0
	if err := sh.Run(); err != nil {
		if ee, ok := err.(*exec.ExitError); ok {
			exitCode = ee.ExitCode()
		} else {
			return "", fmt.Errorf("exec: %w", err)
		}
	}

	var sb strings.Builder
	if outb.Len() > 0 {
		sb.WriteString(outb.String())
	}
	if errb.Len() > 0 {
		if sb.Len() > 0 {
			sb.WriteString("\n--- stderr ---\n")
		}
		sb.WriteString(errb.String())
	}
	sb.WriteString(fmt.Sprintf("\n[exit code: %d]", exitCode))
	return sb.String(), nil
}

// ─── SSE ─────────────────────────────────────────────────────────────────

type SSEWriter struct {
	w       http.ResponseWriter
	flusher http.Flusher
	log     *log.Logger
}

func newSSEWriter(w http.ResponseWriter) *SSEWriter {
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.WriteHeader(200)
	f, ok := w.(http.Flusher)
	if !ok {
		panic("not a flusher")
	}
	return &SSEWriter{w: w, flusher: f, log: log.Default()}
}

func (s *SSEWriter) send(event, data string) {
	escaped := strings.ReplaceAll(data, "\n", "\\n")
	fmt.Fprintf(s.w, "event: %s\ndata: %s\n\n", event, escaped)
	s.flusher.Flush()
	s.log.Printf("[sse] event=%s len=%d", event, len(data))
}

// ─── Chat handler ────────────────────────────────────────────────────────

func handleChat(cfg *RuntimeConfig) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "POST only", 405)
			return
		}

		var req struct {
			Message   string `json:"message"`
			SessionID string `json:"session_id"`
		}
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			log.Printf("[chat] bad request: %v", err)
			http.Error(w, `{"error":"bad request"}`, 400)
			return
		}
		if strings.TrimSpace(req.Message) == "" {
			w.Header().Set("Content-Type", "text/event-stream")
			newSSEWriter(w).send("error", "Message cannot be empty.")
			return
		}

		apiKey, baseURL, model, systemPrompt, maxIter := cfg.Get()

		if apiKey == "" || baseURL == "" || model == "" {
			log.Printf("[chat] missing config")
			w.Header().Set("Content-Type", "text/event-stream")
			newSSEWriter(w).send("error", "Configuration incomplete: set API Key, Base URL, and Model in Settings.")
			return
		}

		ss := newSSEWriter(w)

		// resolve session
		sess := getSession(req.SessionID)
		if sess == nil {
			sess = createSession()
			ss.send("session", sess.ID)
			log.Printf("[chat] new session %s", sess.ID)
		}

		// append user message
		sess.Messages = append(sess.Messages, Message{Role: "user", Content: req.Message})

		// build full message list with system prompt
		msgs := make([]Message, 0, 1+len(sess.Messages))
		msgs = append(msgs, Message{Role: "system", Content: systemPrompt})
		msgs = append(msgs, sess.Messages...)

		for i := 0; i < maxIter; i++ {
			log.Printf("[chat] iter=%d session=%s msgs=%d", i, sess.ID, len(msgs))

			reply, err := callAI(apiKey, baseURL, model, msgs)
			if err != nil {
				errMsg := fmt.Sprintf("AI call failed: %v", err)
				log.Printf("[chat] ERROR: %s", errMsg)
				ss.send("error", errMsg)
				return
			}

			// check for <done>
			if summary, ok := parseTag(reply, "done"); ok {
				natural := stripTags(reply)
				if natural == "" {
					natural = summary
				}
				log.Printf("[chat] done: session=%s", sess.ID)
				ss.send("assistant", natural)
				sess.Messages = append(sess.Messages, Message{Role: "assistant", Content: natural})
				return
			}

			// check for <cmd>
			if cmdStr, ok := parseTag(reply, "cmd"); ok {
				norm := strings.TrimSpace(cmdStr)

				// dedup: if same command already ran → force summary
				dupe := false
				for _, m := range sess.Messages {
					if m.Role == "system" && strings.HasPrefix(m.Content, "[cmd-output] "+norm+"\n") {
						dupe = true
						break
					}
				}
				if dupe {
					log.Printf("[chat] dedup loop detected session=%s cmd=%q", sess.ID, norm)
					forcedSummary(ss, sess, "")
					return
				}

				ss.send("cmd", norm)
				sess.Messages = append(sess.Messages, Message{Role: "assistant", Content: reply})

				result, err := runCmd(norm)
				if err != nil {
					errMsg := fmt.Sprintf("Command execution failed: %v", err)
					log.Printf("[chat] ERROR: %s", errMsg)
					ss.send("error", errMsg)
					return
				}
				log.Printf("[chat] cmd ok: session=%s exit=0 outlen=%d", sess.ID, len(result))
				ss.send("result", result)
				sess.Messages = append(sess.Messages, Message{Role: "system", Content: "[cmd-output] " + norm + "\n" + result})
				continue
			}

			// no tags → natural answer
			log.Printf("[chat] natural answer: session=%s", sess.ID)
			ss.send("assistant", reply)
			sess.Messages = append(sess.Messages, Message{Role: "assistant", Content: reply})
			return
		}

		log.Printf("[chat] max iterations reached session=%s", sess.ID)
		forcedSummary(ss, sess, "")
	}
}

// forcedSummary builds a summary from the last command output without
// calling the AI again, avoiding potential API errors.
func forcedSummary(ss *SSEWriter, sess *Session, prefix string) {
	var output string
	for i := len(sess.Messages) - 1; i >= 0; i-- {
		if sess.Messages[i].Role == "system" && strings.Contains(sess.Messages[i].Content, "[cmd-output]") {
			output = sess.Messages[i].Content
			break
		}
	}
	if output == "" {
		msg := "Task completed."
		if prefix != "" {
			msg = prefix + "\n" + msg
		}
		ss.send("assistant", msg)
		sess.Messages = append(sess.Messages, Message{Role: "assistant", Content: msg})
		return
	}

	// strip [cmd-output] prefix, keep just the result
	lines := strings.SplitN(output, "\n", 2)
	result := ""
	if len(lines) == 2 {
		result = strings.TrimSpace(lines[1])
		// further strip trailing [exit code: N] if present
		if idx := strings.LastIndex(result, "[exit code:"); idx >= 0 {
			before := strings.TrimSpace(result[:idx])
			exitLine := strings.TrimSpace(result[idx:])
			if before != "" {
				result = before + "\n" + exitLine
			} else {
				result = exitLine
			}
		}
	}
	if result == "" {
		result = "Task completed."
	}
	// truncate very long output
	if len(result) > 500 {
		result = result[:500] + "\n… (truncated)"
	}
	reply := result
	if prefix != "" {
		reply = prefix + "\n" + reply
	}
	ss.send("assistant", reply)
	sess.Messages = append(sess.Messages, Message{Role: "assistant", Content: reply})
}

// ─── Config API ──────────────────────────────────────────────────────────

func handleGetConfig(cfg *RuntimeConfig) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		apiKey, baseURL, model, systemPrompt, maxIter := cfg.Get()
		masked := ""
		if len(apiKey) > 8 {
			masked = apiKey[:4] + "…" + apiKey[len(apiKey)-4:]
		} else if apiKey != "" {
			masked = "…set…"
		}
		json.NewEncoder(w).Encode(map[string]interface{}{
			"api_key":       masked,
			"api_key_set":   apiKey != "",
			"base_url":      baseURL,
			"model":         model,
			"system_prompt": systemPrompt,
			"max_iter":      maxIter,
		})
	}
}

func handleSetConfig(cfg *RuntimeConfig) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != "POST" {
			http.Error(w, "POST only", 405)
			return
		}
		var body struct {
			APIKey       string `json:"api_key"`
			BaseURL      string `json:"base_url"`
			Model        string `json:"model"`
			SystemPrompt string `json:"system_prompt"`
			MaxIter      int    `json:"max_iter"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			http.Error(w, `{"error":"bad request"}`, 400)
			return
		}
		cfg.Set(body.APIKey, body.BaseURL, body.Model, body.SystemPrompt, body.MaxIter)
		log.Printf("[config] updated: model=%s max_iter=%d prompt_len=%d", body.Model, body.MaxIter, len(body.SystemPrompt))
		json.NewEncoder(w).Encode(map[string]string{"status": "ok"})
	}
}

// ─── Main ────────────────────────────────────────────────────────────────

func main() {
	log.SetFlags(log.Ltime | log.Lmsgprefix)
	log.SetPrefix("")

	initConfig()

	var err error
	cwd, err = os.Getwd()
	if err != nil {
		log.Fatalf("Getwd: %v", err)
	}

	// static files
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("static"))))

	// API
	http.HandleFunc("/api/chat", handleChat(rcfg))
	http.HandleFunc("/api/config", func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "POST" {
			handleSetConfig(rcfg)(w, r)
		} else {
			handleGetConfig(rcfg)(w, r)
		}
	})

	// SPA fallback
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		http.ServeFile(w, r, "static/index.html")
	})

	addr := ":8080"
	log.Printf("Listening on http://localhost%s", addr)
	log.Fatal(http.ListenAndServe(addr, nil))
}
