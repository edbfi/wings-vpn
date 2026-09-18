package config

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestConfigurationYAMLRoundTrip(t *testing.T) {
	previousConfig, previousJWT := _config, _jwtAlgo
	t.Cleanup(func() { _config, _jwtAlgo = previousConfig, previousJWT })
	t.Setenv("WINGS_TOKEN_ID", "environment-id")
	t.Setenv("WINGS_TOKEN", "environment-token")
	filename := filepath.Join(t.TempDir(), "config.yml")
	// Existing YAML 1.1 booleans, aliases and omitted defaults must keep working.
	input := `debug: yes
quiet: off
app_name: "on"
token_id: file-id
token: file-token
api:
  port: 8443
  ssl:
    enabled: on
allowed_mounts: &mounts
  - /srv/example
allowed_origins: *mounts
`
	if err := os.WriteFile(filename, []byte(input), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := FromFile(filename); err != nil {
		t.Fatal(err)
	}
	c := Get()
	if !c.Debug || c.Quiet || !c.Api.Ssl.Enabled || c.AppName != "on" {
		t.Fatal("legacy booleans or string configuration changed")
	}
	if c.Api.Port != 8443 || c.Api.Host != "0.0.0.0" || c.System.Sftp.Port != 2022 {
		t.Fatal("explicit values or omitted defaults changed")
	}
	if len(c.AllowedMounts) != 1 || len(c.AllowedOrigins) != 1 || c.AllowedOrigins[0] != "/srv/example" {
		t.Fatal("YAML alias was not resolved")
	}
	if c.Token.ID != "environment-id" || c.Token.Token != "environment-token" {
		t.Fatal("environment token override was not applied")
	}
	if err := WriteToDisk(c); err != nil {
		t.Fatal(err)
	}
	contents, err := os.ReadFile(filename)
	if err != nil {
		t.Fatal(err)
	}
	if strings.Contains(string(contents), "environment-") || !strings.Contains(string(contents), "\n  port: 8443\n") {
		t.Fatal("writing leaked the runtime token or changed the two-space indentation")
	}
	info, err := os.Stat(filename)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("configuration permissions = %v, want 0600", info.Mode().Perm())
	}
	t.Setenv("WINGS_TOKEN_ID", "")
	t.Setenv("WINGS_TOKEN", "")
	if err := FromFile(filename); err != nil {
		t.Fatal(err)
	}
	c = Get()
	if c.Token.ID != "file-id" || c.Token.Token != "file-token" || !c.Api.Ssl.Enabled || c.Api.Port != 8443 {
		t.Fatal("saved configuration did not round-trip")
	}
}

func TestConfigurationYAMLRejectsDuplicateKeys(t *testing.T) {
	filename := filepath.Join(t.TempDir(), "config.yml")
	if err := os.WriteFile(filename, []byte("token: first\ntoken: second\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	if err := FromFile(filename); err == nil {
		t.Fatal("ambiguous duplicate token keys must be rejected")
	}
}
