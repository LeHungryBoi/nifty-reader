package api

import (
	"net/http"
	"net/url"
	"time"
)

// Client 封装 HTTP 客户端配置
type Client struct {
	httpClient *http.Client
	proxyURL   string
}

// NewClient 创建新的 API 客户端
// proxyURL: 可选的代理地址，如 "http://127.0.0.1:7890"
func NewClient(proxyURL string) *Client {
	transport := &http.Transport{}
	if proxyURL != "" {
		if proxy, err := url.Parse(proxyURL); err == nil {
			transport.Proxy = http.ProxyURL(proxy)
		}
	}
	return &Client{
		httpClient: &http.Client{
			Transport: transport,
			Timeout:   30 * time.Second,
		},
		proxyURL: proxyURL,
	}
}

// WithTimeout 设置自定义超时
func (c *Client) WithTimeout(timeout time.Duration) *Client {
	c.httpClient.Timeout = timeout
	return c
}
