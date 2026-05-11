package main

import (
	"encoding/csv"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
)

// ── Data structures ──────────────────────────────────────────────

type CsvData struct {
	Headers []string   `json:"headers"`
	Rows    [][]string `json:"rows"`
}

type CellPosition struct {
	Row int `json:"row"`
	Col int `json:"col"`
}

type Selection struct {
	Type    string         `json:"type"` // NONE, ROWS, COLUMNS, CELLS
	Indices []int          `json:"indices"`
	Cells   []CellPosition `json:"cells"`
}

type ActionType string

const (
	TypeShellCommand  ActionType = "SHELL_COMMAND"
	TypeFindReplace   ActionType = "FIND_REPLACE"
	TypeTransform     ActionType = "TRANSFORM"
	TypeToUpper       ActionType = "TO_UPPER"
	TypeToLower       ActionType = "TO_LOWER"
	TypeTrim          ActionType = "TRIM"
	TypePrefix        ActionType = "PREFIX"
	TypeSuffix        ActionType = "SUFFIX"
)

type ActionDefinition struct {
	ID                 string     `json:"id"`
	Name               string     `json:"name"`
	Description        string     `json:"description"`
	Type               ActionType `json:"type"`
	CommandTemplate    string     `json:"commandTemplate"`
	FindText           string     `json:"findText"`
	ReplaceText        string     `json:"replaceText"`
	TransformExpression string    `json:"transformExpression"`
	IncludeHeader      bool       `json:"includeHeader"`
}

// ── JSON response wrapper ───────────────────────────────────────

type DataResponse struct {
	Headers  []string   `json:"headers"`
	Rows     [][]string `json:"rows"`
	Selection Selection `json:"selection"`
	Status   string     `json:"status"`
	FilePath string     `json:"filePath"`
	FileName string     `json:"fileName"`
	RowCount int        `json:"rowCount"`
	ColCount int        `json:"colCount"`
}

// ── App state ────────────────────────────────────────────────────

type AppState struct {
	DataDir      string
	CsvData      *CsvData
	CurrentFile  string
	StatusMsg    string
	Selection    Selection
	Actions      []ActionDefinition
}

func NewAppState(dataDir string) *AppState {
	return &AppState{
		DataDir:   dataDir,
		CsvData:   NewCsvData(),
		Selection: Selection{Type: "NONE"},
		StatusMsg: "Ready",
	}
}

func NewCsvData() *CsvData {
	return &CsvData{
		Headers: []string{"Column 1", "Column 2", "Column 3"},
		Rows: [][]string{
			{"", "", ""},
			{"", "", ""},
			{"", "", ""},
		},
	}
}

func (d *CsvData) GetCell(row, col int) string {
	if row >= 0 && row < len(d.Rows) && col >= 0 && col < len(d.Headers) {
		return d.Rows[row][col]
	}
	return ""
}

func (d *CsvData) SetCell(row, col int, value string) {
	if row >= 0 && row < len(d.Rows) && col >= 0 && col < len(d.Rows[row]) {
		d.Rows[row][col] = value
	}
}

func (d *CsvData) AddRow() {
	d.Rows = append(d.Rows, make([]string, len(d.Headers)))
}

func (d *CsvData) DeleteRow(index int) {
	if index >= 0 && index < len(d.Rows) {
		d.Rows = append(d.Rows[:index], d.Rows[index+1:]...)
	}
}

func (d *CsvData) AddColumn(header string) {
	d.Headers = append(d.Headers, header)
	for i := range d.Rows {
		d.Rows[i] = append(d.Rows[i], "")
	}
}

func (d *CsvData) DeleteColumn(index int) {
	if index >= 0 && index < len(d.Headers) {
		d.Headers = append(d.Headers[:index], d.Headers[index+1:]...)
		for i := range d.Rows {
			if index < len(d.Rows[i]) {
				d.Rows[i] = append(d.Rows[i][:index], d.Rows[i][index+1:]...)
			}
		}
	}
}

func (d *CsvData) RowCount() int { return len(d.Rows) }
func (d *CsvData) ColCount() int { return len(d.Headers) }

// ── CSV file I/O ─────────────────────────────────────────────────

func ReadCsvFile(path string) (*CsvData, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	reader := csv.NewReader(f)
	reader.LazyQuotes = true
	records, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}

	if len(records) == 0 {
		return NewCsvData(), nil
	}

	data := &CsvData{
		Headers: records[0],
	}
	for i := 1; i < len(records); i++ {
		row := records[i]
		// Pad or truncate to match header count
		for len(row) < len(data.Headers) {
			row = append(row, "")
		}
		if len(row) > len(data.Headers) {
			row = row[:len(data.Headers)]
		}
		data.Rows = append(data.Rows, row)
	}
	return data, nil
}

func WriteCsvFile(data *CsvData, path string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	writer := csv.NewWriter(f)
	defer writer.Flush()

	if err := writer.Write(data.Headers); err != nil {
		return err
	}
	for _, row := range data.Rows {
		if err := writer.Write(row); err != nil {
			return err
		}
	}
	return nil
}

// ── File listing ─────────────────────────────────────────────────

func ListCsvFiles(dir string) []string {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil
	}
	var files []string
	for _, e := range entries {
		if !e.IsDir() && strings.HasSuffix(strings.ToLower(e.Name()), ".csv") {
			files = append(files, e.Name())
		}
	}
	sort.Strings(files)
	return files
}

func (s *AppState) MakeResponse() *DataResponse {
	fileName := ""
	if s.CurrentFile != "" {
		fileName = filepath.Base(s.CurrentFile)
	}
	return &DataResponse{
		Headers:   s.CsvData.Headers,
		Rows:      s.CsvData.Rows,
		Selection: s.Selection,
		Status:    s.StatusMsg,
		FilePath:  s.CurrentFile,
		FileName:  fileName,
		RowCount:  s.CsvData.RowCount(),
		ColCount:  s.CsvData.ColCount(),
	}
}

func (s *AppState) ListCsvs() []string { return ListCsvFiles(s.DataDir) }

// ── Shell escaping ───────────────────────────────────────────────

func escapeShell(val string) string {
	return "'" + strings.ReplaceAll(val, "'", "'\\''") + "'"
}

func (s *AppState) SetStatus(msg string, args ...interface{}) {
	if len(args) > 0 {
		s.StatusMsg = fmt.Sprintf(msg, args...)
	} else {
		s.StatusMsg = msg
	}
}
