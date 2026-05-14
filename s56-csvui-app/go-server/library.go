package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

const libraryFileName = "action-library.json"

func libraryFilePath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	dir := filepath.Join(home, ".csv-tabulator")
	if err := os.MkdirAll(dir, 0755); err != nil {
		return "", err
	}
	return filepath.Join(dir, libraryFileName), nil
}

func LoadActionLibrary() []ActionDefinition {
	path, err := libraryFilePath()
	if err != nil {
		return getDefaultActions()
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return getDefaultActions()
	}

	var actions []ActionDefinition
	if err := json.Unmarshal(data, &actions); err != nil {
		return getDefaultActions()
	}

	// Ensure we have defaults
	defaults := getDefaultActions()
	for _, d := range defaults {
		found := false
		for _, a := range actions {
			if a.Name == d.Name && a.Type == d.Type {
				found = true
				break
			}
		}
		if !found {
			actions = append(actions, d)
		}
	}
	return actions
}

func SaveActionLibrary(actions []ActionDefinition) error {
	path, err := libraryFilePath()
	if err != nil {
		return err
	}

	data, err := json.MarshalIndent(actions, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0644)
}

func getDefaultActions() []ActionDefinition {
	return []ActionDefinition{
		{
			ID:   "rev",
			Name: "Reverse Text",
			Description: "Reverses the text in each selected cell",
			Type: TypeTransform,
			TransformExpression: "reverse",
		},
		{
			ID:   "len",
			Name: "Get Length",
			Description: "Replaces cell content with its character length",
			Type: TypeTransform,
			TransformExpression: "length",
		},
		{
			ID:   "wc",
			Name: "Count Words (wc)",
			Description: "Counts words in each cell using wc command",
			Type: TypeShellCommand,
			CommandTemplate: "echo {cell} | wc -w",
		},
		{
			ID:   "sha",
			Name: "To SHA256",
			Description: "Computes SHA256 hash of cell content",
			Type: TypeShellCommand,
			CommandTemplate: "echo -n {cell} | sha256sum | cut -d' ' -f1",
		},
		{
			ID:   "urlenc",
			Name: "URL Encode",
			Description: "URL-encodes cell content using Python",
			Type: TypeShellCommand,
			CommandTemplate: fmt.Sprintf(`python3 -c "import urllib.parse; print(urllib.parse.quote('%s'))"`, "{cell}"),
		},
	}
}

func (s *AppState) loadActions() {
	s.Actions = LoadActionLibrary()
}

func (s *AppState) saveActions() {
	SaveActionLibrary(s.Actions)
}
