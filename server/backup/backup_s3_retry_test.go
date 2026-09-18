package backup

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestUploadPartRetryPolicy(t *testing.T) {
	for _, tc := range []struct {
		name       string
		first      int
		attempts   int32
		shouldFail bool
	}{
		{name: "success", first: http.StatusOK, attempts: 1},
		{name: "permanent", first: http.StatusForbidden, attempts: 1, shouldFail: true},
		{name: "transient", first: http.StatusServiceUnavailable, attempts: 2},
	} {
		t.Run(tc.name, func(t *testing.T) {
			var attempts atomic.Int32
			server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
				w.Header().Set("ETag", "part-etag")
				if attempts.Add(1) == 1 {
					w.WriteHeader(tc.first)
				}
			}))
			defer server.Close()
			uploader := newS3FileUploader(io.NopCloser(strings.NewReader("")))
			uploader.client = server.Client()
			etag, err := uploader.uploadPart(context.Background(), server.URL, 0)
			if tc.shouldFail {
				assert.ErrorContains(t, err, "HTTP/403")
				assert.Empty(t, etag)
			} else {
				assert.NoError(t, err)
				assert.Equal(t, "part-etag", etag)
			}
			assert.Equal(t, tc.attempts, attempts.Load())
		})
	}
}

func TestUploadPartCancellationStopsRetryWait(t *testing.T) {
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	var attempts atomic.Int32
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		attempts.Add(1)
		w.WriteHeader(http.StatusServiceUnavailable)
		cancel()
	}))
	defer server.Close()
	uploader := newS3FileUploader(io.NopCloser(strings.NewReader("")))
	uploader.client = server.Client()
	etag, err := uploader.uploadPart(ctx, server.URL, 0)
	assert.Empty(t, etag)
	assert.ErrorIs(t, err, context.Canceled)
	assert.Equal(t, int32(1), attempts.Load())
}
