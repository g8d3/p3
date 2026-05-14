package main

import (
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

// ── Action interface ─────────────────────────────────────────────

type Action interface {
	Name() string
	Apply(data *CsvData, sel Selection) *CsvData
}

// ── Action factory ───────────────────────────────────────────────

func CreateAction(def ActionDefinition) Action {
	switch def.Type {
	case TypeToUpper:
		return &builtinAction{name: def.Name, fn: strings.ToUpper}
	case TypeToLower:
		return &builtinAction{name: def.Name, fn: strings.ToLower}
	case TypeTrim:
		return &builtinAction{name: def.Name, fn: strings.TrimSpace}
	case TypeFindReplace:
		return &findReplaceAction{name: def.Name, find: def.FindText, replace: def.ReplaceText}
	case TypeTransform:
		return &transformAction{name: def.Name, expr: def.TransformExpression}
	case TypePrefix:
		return &prefixAction{name: def.Name, prefix: def.FindText}
	case TypeSuffix:
		return &suffixAction{name: def.Name, suffix: def.FindText}
	case TypeShellCommand:
		return &shellAction{name: def.Name, template: def.CommandTemplate, includeHeader: def.IncludeHeader}
	}
	return nil
}

// ── Get cells from selection ─────────────────────────────────────

func getApplicableCells(data *CsvData, sel Selection) []CellPosition {
	switch sel.Type {
	case "NONE":
		return nil
	case "ROWS":
		var cells []CellPosition
		for _, r := range sel.Indices {
			if r >= 0 && r < len(data.Rows) {
				for c := 0; c < len(data.Headers); c++ {
					cells = append(cells, CellPosition{Row: r, Col: c})
				}
			}
		}
		return cells
	case "COLUMNS":
		var cells []CellPosition
		for _, c := range sel.Indices {
			if c >= 0 && c < len(data.Headers) {
				for r := 0; r < len(data.Rows); r++ {
					cells = append(cells, CellPosition{Row: r, Col: c})
				}
			}
		}
		return cells
	case "CELLS":
		return sel.Cells
	}
	return nil
}

// ── Built-in: single function transform ──────────────────────────

type builtinAction struct {
	name string
	fn   func(string) string
}

func (a *builtinAction) Name() string { return a.name }
func (a *builtinAction) Apply(data *CsvData, sel Selection) *CsvData {
	result := copyData(data)
	for _, c := range getApplicableCells(result, sel) {
		result.SetCell(c.Row, c.Col, a.fn(result.GetCell(c.Row, c.Col)))
	}
	return result
}

// ── Find & Replace ───────────────────────────────────────────────

type findReplaceAction struct {
	name    string
	find    string
	replace string
}

func (a *findReplaceAction) Name() string { return a.name }
func (a *findReplaceAction) Apply(data *CsvData, sel Selection) *CsvData {
	result := copyData(data)
	for _, c := range getApplicableCells(result, sel) {
		val := result.GetCell(c.Row, c.Col)
		result.SetCell(c.Row, c.Col, strings.ReplaceAll(val, a.find, a.replace))
	}
	return result
}

// ── Transform (reverse, length, substr, padLeft, padRight, repeat, replace) ──

type transformAction struct {
	name string
	expr string
}

func (a *transformAction) Name() string { return a.name }
func (a *transformAction) Apply(data *CsvData, sel Selection) *CsvData {
	result := copyData(data)
	for _, c := range getApplicableCells(result, sel) {
		val := result.GetCell(c.Row, c.Col)
		result.SetCell(c.Row, c.Col, applyTransform(val, a.expr))
	}
	return result
}

func applyTransform(val, expr string) string {
	e := strings.TrimSpace(expr)
	switch {
	case e == "reverse":
		runes := []rune(val)
		for i, j := 0, len(runes)-1; i < j; i, j = i+1, j-1 {
			runes[i], runes[j] = runes[j], runes[i]
		}
		return string(runes)

	case e == "length":
		return strconv.Itoa(len([]rune(val)))

	case strings.HasPrefix(e, "substr("):
		// substr(start) or substr(start,length)
		inner := strings.TrimSuffix(strings.TrimPrefix(e, "substr("), ")")
		parts := strings.Split(inner, ",")
		start := 0
		if len(parts) > 0 {
			start, _ = strconv.Atoi(strings.TrimSpace(parts[0]))
		}
		runes := []rune(val)
		if start < 0 {
			start = 0
		}
		if start >= len(runes) {
			return ""
		}
		if len(parts) >= 2 {
			length, _ := strconv.Atoi(strings.TrimSpace(parts[1]))
			if length < 0 {
				length = 0
			}
			end := start + length
			if end > len(runes) {
				end = len(runes)
			}
			return string(runes[start:end])
		}
		return string(runes[start:])

	case strings.HasPrefix(e, "repeat("):
		inner := strings.TrimSuffix(strings.TrimPrefix(e, "repeat("), ")")
		n, _ := strconv.Atoi(strings.TrimSpace(inner))
		if n < 0 {
			n = 0
		}
		return strings.Repeat(val, n)

	case strings.HasPrefix(e, "padLeft("):
		inner := strings.TrimSuffix(strings.TrimPrefix(e, "padLeft("), ")")
		parts := strings.Split(inner, ",")
		if len(parts) >= 1 {
			n, _ := strconv.Atoi(strings.TrimSpace(parts[0]))
			ch := byte(' ')
			if len(parts) >= 2 {
				s := strings.TrimSpace(parts[1])
				s = strings.Trim(s, "\"'")
				if len(s) > 0 {
					ch = s[0]
				}
			}
			runes := []rune(val)
			if len(runes) < n {
				return strings.Repeat(string(ch), n-len(runes)) + val
			}
		}
		return val

	case strings.HasPrefix(e, "padRight("):
		inner := strings.TrimSuffix(strings.TrimPrefix(e, "padRight("), ")")
		parts := strings.Split(inner, ",")
		if len(parts) >= 1 {
			n, _ := strconv.Atoi(strings.TrimSpace(parts[0]))
			ch := byte(' ')
			if len(parts) >= 2 {
				s := strings.TrimSpace(parts[1])
				s = strings.Trim(s, "\"'")
				if len(s) > 0 {
					ch = s[0]
				}
			}
			runes := []rune(val)
			if len(runes) < n {
				return val + strings.Repeat(string(ch), n-len(runes))
			}
		}
		return val

	case strings.HasPrefix(e, "replace("):
		// replace("old","new")
		inner := strings.TrimSuffix(strings.TrimPrefix(e, "replace("), ")")
		parts := splitReplaceArgs(inner)
		if len(parts) >= 2 {
			old := strings.Trim(parts[0], "\"'")
			newStr := strings.Trim(parts[1], "\"'")
			return strings.ReplaceAll(val, old, newStr)
		}
		return val
	}
	return val
}

func splitReplaceArgs(s string) []string {
	// Simple split considering quoted strings
	var result []string
	var current strings.Builder
	inQuote := false
	quoteChar := byte(0)
	for i := 0; i < len(s); i++ {
		c := s[i]
		if inQuote {
			current.WriteByte(c)
			if c == quoteChar {
				inQuote = false
			}
		} else if c == '"' || c == '\'' {
			current.WriteByte(c)
			inQuote = true
			quoteChar = c
		} else if c == ',' {
			result = append(result, current.String())
			current.Reset()
		} else {
			current.WriteByte(c)
		}
	}
	if current.Len() > 0 {
		result = append(result, current.String())
	}
	return result
}

// ── Prefix ───────────────────────────────────────────────────────

type prefixAction struct {
	name   string
	prefix string
}

func (a *prefixAction) Name() string { return a.name }
func (a *prefixAction) Apply(data *CsvData, sel Selection) *CsvData {
	result := copyData(data)
	for _, c := range getApplicableCells(result, sel) {
		result.SetCell(c.Row, c.Col, a.prefix+result.GetCell(c.Row, c.Col))
	}
	return result
}

// ── Suffix ───────────────────────────────────────────────────────

type suffixAction struct {
	name   string
	suffix string
}

func (a *suffixAction) Name() string { return a.name }
func (a *suffixAction) Apply(data *CsvData, sel Selection) *CsvData {
	result := copyData(data)
	for _, c := range getApplicableCells(result, sel) {
		result.SetCell(c.Row, c.Col, result.GetCell(c.Row, c.Col)+a.suffix)
	}
	return result
}

// ── Shell command ────────────────────────────────────────────────

type shellAction struct {
	name         string
	template     string
	includeHeader bool
}

func (a *shellAction) Name() string { return a.name }
func (a *shellAction) Apply(data *CsvData, sel Selection) *CsvData {
	result := copyData(data)
	cells := getApplicableCells(result, sel)
	for _, c := range cells {
		val := result.GetCell(c.Row, c.Col)
		if c.Row == 0 && !a.includeHeader {
			// Skip header if not included
		}
		newVal := executeShell(val, a.template)
		result.SetCell(c.Row, c.Col, newVal)
	}
	return result
}

func executeShell(input, template string) string {
	var cmdStr string
	if strings.Contains(template, "{cell}") {
		escaped := escapeShell(input)
		cmdStr = strings.ReplaceAll(template, "{cell}", escaped)
	} else {
		escaped := escapeShell(input)
		cmdStr = fmt.Sprintf("echo %s | %s", escaped, template)
	}

	cmd := exec.Command("sh", "-c", cmdStr)
	output, err := cmd.CombinedOutput()
	outStr := strings.TrimSpace(string(output))
	if err != nil {
		return fmt.Sprintf("[Exit %d] %s", cmd.ProcessState.ExitCode(), outStr)
	}
	return outStr
}

// ── Helper ───────────────────────────────────────────────────────

func copyData(d *CsvData) *CsvData {
	headers := make([]string, len(d.Headers))
	copy(headers, d.Headers)
	rows := make([][]string, len(d.Rows))
	for i, row := range d.Rows {
		r := make([]string, len(row))
		copy(r, row)
		rows[i] = r
	}
	return &CsvData{Headers: headers, Rows: rows}
}
