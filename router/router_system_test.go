package router

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"

	"github.com/pelican/wings/config"
)

func TestConfigurationUpdateCannotReplacePrivatePath(t *testing.T) {
	previous := config.Get()
	t.Cleanup(func() { config.Set(previous) })
	directory := t.TempDir()
	filename := filepath.Join(directory, "config.yml")
	injected := filepath.Join(directory, "unexpected.yml")
	cfg, err := config.NewAtPath(filename)
	if err != nil {
		t.Fatal(err)
	}
	cfg.AuthenticationToken = "test-token"
	config.Set(cfg)
	payload, err := json.Marshal(map[string]string{
		"path": injected, "Path": injected, "app_name": "updated",
	})
	if err != nil {
		t.Fatal(err)
	}
	response := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(response)
	c.Request = httptest.NewRequest(http.MethodPost, "/api/update", bytes.NewReader(payload))
	c.Request.Header.Set("Content-Type", "application/json")
	postUpdateConfiguration(c)
	if response.Code != http.StatusOK || response.Body.String() != `{"applied":true}` {
		t.Fatalf("update response = %d %s", response.Code, response.Body.String())
	}
	contents, err := os.ReadFile(filename)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(contents), "app_name: updated") {
		t.Fatal("configuration update was not saved at its original path")
	}
	if _, err := os.Stat(injected); !os.IsNotExist(err) {
		t.Fatalf("request controlled the configuration path: %v", err)
	}
}
