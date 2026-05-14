package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
)

// ── Request types ────────────────────────────────────────────────

type CellRequest struct {
	Row   int    `json:"row"`
	Col   int    `json:"col"`
	Value string `json:"value"`
}

type RowOpRequest struct {
	Action string `json:"action"` // "add" or "delete"
	Index  int    `json:"index,omitempty"`
}

type ColumnOpRequest struct {
	Action string `json:"action"` // "add" or "delete"
	Index  int    `json:"index,omitempty"`
	Header string `json:"header,omitempty"`
}

type FileOpRequest struct {
	Action string `json:"action"` // "new" or "open"
	Path   string `json:"path,omitempty"`
}

type SaveRequest struct {
	Path string `json:"path,omitempty"`
}

type ExecuteActionRequest struct {
	Action    ActionDefinition `json:"action"`
	Selection Selection        `json:"selection"`
}

// ── JSON helpers ─────────────────────────────────────────────────

func writeJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, msg string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]string{"error": msg})
}

func readBody(r *http.Request, v interface{}) error {
	defer r.Body.Close()
	return json.NewDecoder(r.Body).Decode(v)
}

// ── Handlers ─────────────────────────────────────────────────────

func (s *AppState) handleGetData(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, s.MakeResponse())
}

func (s *AppState) handleGetInfo(w http.ResponseWriter, r *http.Request) {
	fileName := ""
	if s.CurrentFile != "" {
		fileName = filepath.Base(s.CurrentFile)
	}
	info := map[string]interface{}{
		"status":   s.StatusMsg,
		"fileName": fileName,
		"filePath": s.CurrentFile,
		"dataDir":  s.DataDir,
		"rowCount": s.CsvData.RowCount(),
		"colCount": s.CsvData.ColCount(),
	}
	writeJSON(w, info)
}

func (s *AppState) handleUpdateCell(w http.ResponseWriter, r *http.Request) {
	var req CellRequest
	if err := readBody(r, &req); err != nil {
		writeError(w, "Invalid request: "+err.Error(), 400)
		return
	}
	s.CsvData.SetCell(req.Row, req.Col, req.Value)
	s.SetStatus("Cell updated")
	writeJSON(w, s.MakeResponse())
}

func (s *AppState) handleRowOp(w http.ResponseWriter, r *http.Request) {
	var req RowOpRequest
	if err := readBody(r, &req); err != nil {
		writeError(w, "Invalid request: "+err.Error(), 400)
		return
	}
	switch req.Action {
	case "add":
		s.CsvData.AddRow()
		s.SetStatus("Row added")
	case "delete":
		s.CsvData.DeleteRow(req.Index)
		s.Selection = Selection{Type: "NONE"}
		s.SetStatus("Row deleted")
	}
	writeJSON(w, s.MakeResponse())
}

func (s *AppState) handleColumnOp(w http.ResponseWriter, r *http.Request) {
	var req ColumnOpRequest
	if err := readBody(r, &req); err != nil {
		writeError(w, "Invalid request: "+err.Error(), 400)
		return
	}
	switch req.Action {
	case "add":
		header := req.Header
		if header == "" {
			header = fmt.Sprintf("Column %d", s.CsvData.ColCount()+1)
		}
		s.CsvData.AddColumn(header)
		s.SetStatus("Column added")
	case "delete":
		s.CsvData.DeleteColumn(req.Index)
		s.Selection = Selection{Type: "NONE"}
		s.SetStatus("Column deleted")
	case "rename":
		if req.Index >= 0 && req.Index < len(s.CsvData.Headers) && req.Header != "" {
			s.CsvData.Headers[req.Index] = req.Header
			s.SetStatus("Column renamed")
		}
	}
	writeJSON(w, s.MakeResponse())
}

func (s *AppState) handleFileOp(w http.ResponseWriter, r *http.Request) {
	var req FileOpRequest
	if err := readBody(r, &req); err != nil {
		writeError(w, "Invalid request: "+err.Error(), 400)
		return
	}
	switch req.Action {
	case "new":
		s.CsvData = NewCsvData()
		s.CurrentFile = ""
		s.Selection = Selection{Type: "NONE"}
		s.SetStatus("New file")
	case "open":
		path := req.Path
		if path != "" {
			// Try the path as-is first, then in data directory
			absPath := path
			if !filepath.IsAbs(path) {
				// Check if it's a bare filename in the data dir
				candidate := filepath.Join(s.DataDir, filepath.Base(path))
				if _, err := os.Stat(candidate); err == nil {
					absPath = candidate
				} else {
					absPath = filepath.Join(s.DataDir, path)
				}
			}
			if _, err := os.Stat(absPath); err == nil {
				data, err := ReadCsvFile(absPath)
				if err != nil {
					s.SetStatus("Error: " + err.Error())
				} else {
					s.CsvData = data
					s.CurrentFile = absPath
					s.Selection = Selection{Type: "NONE"}
					s.SetStatus("Opened: " + filepath.Base(absPath))
				}
			} else {
				s.SetStatus("File not found: " + path)
			}
		}
	}
	writeJSON(w, s.MakeResponse())
}

func (s *AppState) handleSave(w http.ResponseWriter, r *http.Request) {
	var req SaveRequest
	if err := readBody(r, &req); err != nil {
		// If no body, try saving to current file
		req = SaveRequest{Path: s.CurrentFile}
	}

	path := req.Path
	if path == "" {
		path = s.CurrentFile
	}
	if path == "" {
		// Default save to data dir
		path = filepath.Join(s.DataDir, "untitled.csv")
	}

	if err := WriteCsvFile(s.CsvData, path); err != nil {
		writeError(w, err.Error(), 500)
		return
	}
	s.CurrentFile = path
	s.SetStatus("Saved: " + filepath.Base(path))
	writeJSON(w, s.MakeResponse())
}

func (s *AppState) handleExecuteAction(w http.ResponseWriter, r *http.Request) {
	var req ExecuteActionRequest
	if err := readBody(r, &req); err != nil {
		writeError(w, "Invalid request: "+err.Error(), 400)
		return
	}

	if req.Selection.Type != "NONE" {
		action := CreateAction(req.Action)
		if action != nil {
			s.CsvData = action.Apply(s.CsvData, req.Selection)
			s.SetStatus("Action '%s' applied", action.Name())
		}
	}
	writeJSON(w, s.MakeResponse())
}

func (s *AppState) handleListFiles(w http.ResponseWriter, r *http.Request) {
	files := s.ListCsvs()
	writeJSON(w, files)
}

func (s *AppState) handleListActions(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, s.Actions)
}

func (s *AppState) handleCreateAction(w http.ResponseWriter, r *http.Request) {
	var def ActionDefinition
	if err := readBody(r, &def); err != nil {
		writeError(w, "Invalid request: "+err.Error(), 400)
		return
	}
	if def.ID == "" {
		def.ID = randID()
	}
	s.Actions = append(s.Actions, def)
	s.saveActions()
	s.SetStatus("Action '%s' created", def.Name)
	writeJSON(w, s.Actions)
}

func (s *AppState) handleUpdateAction(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	var def ActionDefinition
	if err := readBody(r, &def); err != nil {
		writeError(w, "Invalid request: "+err.Error(), 400)
		return
	}
	for i := range s.Actions {
		if s.Actions[i].ID == id {
			def.ID = id
			s.Actions[i] = def
			s.saveActions()
			break
		}
	}
	writeJSON(w, s.Actions)
}

func (s *AppState) handleDeleteAction(w http.ResponseWriter, r *http.Request) {
	id := r.PathValue("id")
	for i := range s.Actions {
		if s.Actions[i].ID == id {
			s.Actions = append(s.Actions[:i], s.Actions[i+1:]...)
			s.saveActions()
			break
		}
	}
	writeJSON(w, s.Actions)
}
