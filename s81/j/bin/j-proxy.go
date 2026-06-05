// j-proxy — HTTP reverse proxy that tracks agent state (idle/sending/receiving)
// per tmux agent by matching TCP connections via /proc/<pid>/net/tcp.
//
// Build: go build -o ~/.j/bin/j-proxy ~/.j/bin/j-proxy.go
// Run:   ~/.j/bin/j-proxy
package main

import (
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

var (
	listenAddr = "127.0.0.1:19999"
	upstream   = "https://hyper.charm.land/api/v1/fantasy"
	stateDir   = os.ExpandEnv("$HOME/.j/bus")
)

// ── agent state tracking ──────────────────────────────────────

type agentState struct {
	sync.Mutex
	m map[string]string // agent → idle|sending|receiving
}

var as = &agentState{m: make(map[string]string)}

func setState(agent, s string) {
	as.Lock()
	defer as.Unlock()
	as.m[agent] = s
	fn := filepath.Join(stateDir, ".proxy-"+agent)
	os.WriteFile(fn, []byte(s+"\n"), 0644)
}

func setStateAfter(agent, s string, d time.Duration) {
	go func() {
		time.Sleep(d)
		setState(agent, s)
	}()
}

// ── agent identification via /proc ────────────────────────────

// findByClientPort searches ALL processes' /proc/PID/net/tcp for a
// socket whose local endpoint matches clientIP:clientPort.
func findByClientPort(clientIP, clientPort string) string {
	ip := clientIP
	ip = strings.TrimPrefix(ip, "::ffff:")
	hexIP := ipHex(ip)
	hexPort := fmt.Sprintf("%04X", mustAtoi(clientPort))
	proxyPort := fmt.Sprintf("%04X", mustAtoi(strings.Split(listenAddr, ":")[1]))

	dirs, _ := os.ReadDir("/proc")
	for _, d := range dirs {
		if !d.IsDir() {
			continue
		}
		pid := d.Name()
		if _, err := strconv.Atoi(pid); err != nil {
			continue
		}
		ino := findInodeInProcNet(pid, hexIP, hexPort, proxyPort)
		if ino != "" {
			// Found the client socket — now map PID to tmux agent
			if agent := pidToAgent(pid); agent != "" {
				return agent
			}
		}
	}
	return ""
}

func findInodeInProcNet(pid, hexIP, hexPort, proxyPort string) string {
	for _, fn := range []string{"/proc/" + pid + "/net/tcp", "/proc/" + pid + "/net/tcp6"} {
		data, err := os.ReadFile(fn)
		if err != nil {
			continue
		}
		for _, line := range strings.Split(string(data), "\n") {
			f := strings.Fields(line)
			if len(f) < 10 {
				continue
			}
			local := f[1]  // XXYYZZWW:PPPP
			remote := f[2] // XXYYZZWW:PPPP
			lparts := strings.Split(local, ":")
			rparts := strings.Split(remote, ":")
			if len(lparts) == 2 && len(rparts) == 2 &&
				lparts[0] == hexIP && lparts[1] == hexPort &&
				rparts[1] == proxyPort {
				return f[9] // inode
			}
		}
	}
	return ""
}

func ipHex(ip string) string {
	p := net.ParseIP(ip)
	if p == nil {
		return ""
	}
	if p4 := p.To4(); p4 != nil {
		return fmt.Sprintf("%02X%02X%02X%02X", p4[0], p4[1], p4[2], p4[3])
	}
	// IPv6
	p16 := p.To16()
	var parts []string
	for i := 0; i < 16; i += 4 {
		v := uint32(p16[i]) | uint32(p16[i+1])<<8 | uint32(p16[i+2])<<16 | uint32(p16[i+3])<<24
		parts = append(parts, fmt.Sprintf("%08X", v))
	}
	return strings.Join(parts, "")
}

// ── PID → tmux agent mapping ─────────────────────────────────

var (
	pidAgentMap   map[string]string
	pidAgentMu    sync.Mutex
	pidAgentTs    time.Time
)

func pidToAgent(pid string) string {
	pidAgentMu.Lock()
	defer pidAgentMu.Unlock()

	if pidAgentMap == nil || time.Since(pidAgentTs) > 3*time.Second {
		pidAgentMap = buildPIDAgentMap()
		pidAgentTs = time.Now()
	}

	return walkParentChain(pid)
}

func walkParentChain(pid string) string {
	seen := map[string]bool{}
	for p := pid; p != "" && !seen[p]; {
		seen[p] = true
		if name, ok := pidAgentMap[p]; ok {
			return name
		}
		p = ppid(p)
	}
	return ""
}

func ppid(pid string) string {
	data, err := os.ReadFile(filepath.Join("/proc", pid, "status"))
	if err != nil {
		return ""
	}
	re := regexp.MustCompile(`PPid:\s+(\d+)`)
	m := re.FindStringSubmatch(string(data))
	if m == nil {
		return ""
	}
	return m[1]
}

func buildPIDAgentMap() map[string]string {
	m := make(map[string]string)
	out, err := exec.Command("tmux", "list-panes", "-a", "-F",
		"#{pane_pid}|#{window_name}|#{session_name}").Output()
	if err != nil {
		return m
	}
	for _, line := range strings.Split(strings.TrimSpace(string(out)), "\n") {
		parts := strings.Split(line, "|")
		if len(parts) >= 2 {
			m[parts[0]] = parts[1]
		}
	}
	return m
}

func mustAtoi(s string) int {
	v, _ := strconv.Atoi(s)
	return v
}

// ── HTTP reverse proxy ────────────────────────────────────────

type handler struct {
	upstream *url.URL
	client   *http.Client
}

func newHandler(upstreamURL string) *handler {
	u, _ := url.Parse(upstreamURL)
	return &handler{
		upstream: u,
		client: &http.Client{
			Transport: &http.Transport{
				TLSClientConfig: &tls.Config{InsecureSkipVerify: false},
				MaxIdleConns:    100,
				IdleConnTimeout: 90 * time.Second,
			},
			Timeout: 0,
		},
	}
}

func (h *handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	host, port, _ := net.SplitHostPort(r.RemoteAddr)
	agent := findByClientPort(host, port)
	if agent == "" {
		agent = "unknown"
	}

	switch r.URL.Path {
	case "/__state__", "/state":
		as.Lock()
		list := make([]map[string]string, 0, len(as.m))
		for a, s := range as.m {
			list = append(list, map[string]string{"agent": a, "state": s})
		}
		as.Unlock()
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(list)
		return
	case "/__health__", "/health":
		w.Write([]byte(`{"status":"ok"}`))
		return
	}

	setState(agent, "sending")

	// Build upstream URL
	upstreamPath := h.upstream.Path + r.URL.Path
	if r.URL.RawQuery != "" {
		upstreamPath += "?" + r.URL.RawQuery
	}

	u := h.upstream.Scheme + "://" + h.upstream.Host + upstreamPath
	upReq, err := http.NewRequest(r.Method, u, r.Body)
	if err != nil {
		setState(agent, "idle")
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}

	for k, vs := range r.Header {
		for _, v := range vs {
			upReq.Header.Add(k, v)
		}
	}
	upReq.Header.Set("X-Agent-Name", agent)
	upReq.Host = h.upstream.Host

	resp, err := h.client.Do(upReq)
	if err != nil {
		setState(agent, "idle")
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}
	defer resp.Body.Close()

	setState(agent, "receiving")

	for k, vs := range resp.Header {
		for _, v := range vs {
			w.Header().Add(k, v)
		}
	}
	w.WriteHeader(resp.StatusCode)
	io.Copy(w, resp.Body)

	setState(agent, "idle")
}

// ── main ──────────────────────────────────────────────────────

func main() {
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	if len(os.Args) > 1 && os.Args[1] == "--install" {
		install()
		return
	}

	os.MkdirAll(stateDir, 0755)

	h := newHandler(upstream)
	srv := &http.Server{Addr: listenAddr, Handler: h}

	log.Printf("j-proxy on %s → %s", listenAddr, upstream)
	log.Printf("State: http://%s/__state__", listenAddr)

	if err := srv.ListenAndServe(); err != nil {
		log.Fatal(err)
	}
}

func install() {
	home := os.ExpandEnv("$HOME")
	target := filepath.Join(home, ".local", "share", "crush", "hyper.json")
	self := filepath.Join(home, ".j", "bin", "j-proxy")

	// Build
	cmd := exec.Command("go", "build", "-o", self, os.Args[0])
	cmd.Stderr = os.Stderr
	cmd.Stdout = os.Stdout
	if err := cmd.Run(); err != nil {
		log.Fatalf("build: %v", err)
	}
	log.Printf("binary → %s", self)

	// Backup + update hyper.json
	data, err := os.ReadFile(target)
	if err != nil {
		log.Fatalf("read %s: %v", target, err)
	}
	backup := target + ".bak." + strconv.FormatInt(time.Now().Unix(), 10)
	os.WriteFile(backup, data, 0644)
	log.Printf("backup → %s", backup)

	replaced := strings.Replace(string(data),
		"https://hyper.charm.land/api/v1/fantasy",
		"http://127.0.0.1:19999/api/v1/fantasy", 1)
	if replaced == string(data) {
		log.Fatalf("endpoint not found in %s", target)
	}
	os.WriteFile(target, []byte(replaced), 0644)
	log.Printf("hyper.json updated → proxy")

	log.Printf("Run: %s", self)
	log.Printf("Restart agents for changes to take effect")
}
