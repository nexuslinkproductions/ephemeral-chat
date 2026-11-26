# 05 Transport hardening: undetectability, IP hiding, swarm resistance

RUN: w1-ephemeral-hardening-20261126. Lane 5 of 7.
Inputs: `input/ephemeral-chat-v1.html` (V1, 35598 bytes), `input/ephemeral-chat-overview.pdf`.
Scope: what the transport exposes today, options to hide peer IPs, ranked undetectability options, inbound gating for a serverless app, what a swarm can target, and default deny for a future hosted entry.

## Method and tags

Two kinds of evidence appear below. Claims about the app carry `file:line` references into `input/ephemeral-chat-v1.html`. External claims carry a URL that was fetched during this run and whose title or body matched the claim. One empirical probe was run: the current build was loaded in a real Chromium, an invite was generated, and the resulting code was decoded. That decode is the primary evidence for section 1.

Every option that needs standing infrastructure carries the literal tag `[INFRA]`. The tag means someone must run or rent a host that is up when the two peers are not. Options with no tag work from a static file and two browsers. `[INFRA]` is the form-factor tripwire, not a judgement.

Observer models used throughout. Every option below states which ones it defeats.

| ID | Observer | Sees | Can do |
|---|---|---|---|
| O1 | Passive on-path (ISP, campus, cafe, backbone tap) | 5-tuple, packet sizes, timing, protocol headers | Classify, log, correlate. Cannot read DTLS payload |
| O2 | Active on-path DPI or firewall | Same as O1, plus ability to inject and drop | Fingerprint, block by protocol or SNI, probe, throttle |
| O3 | Signaling-channel observer (email, chat, SMS, clipboard sync) | The full invite and reply codes | Read both IPs and ports, substitute codes, race to answer |
| O4 | Third-party operator (STUN, TURN, VPN, CDN, Tor guard) | Source IP, destination, volume, timing. Not content | Log, correlate, deny service, disclose under pressure |
| O5 | The peer | Your IP and port unless relayed, plus timing and volume | Scan, log, attack your browser after authentication |
| O6 | Global passive adversary watching both ends | Both access links simultaneously | Correlate timing and volume end to end |

O6 is out of reach for everything in this document except partially Tor, and Tor's own position is that it does not defend against O6 (https://blog.torproject.org/quick-summary-recent-traffic-correlation-using-netflows: "The Tor network design, however, does not protect against a targeted attack by a global passive adversary ... watching and measuring Tor traffic going into and out of the network and correlating the information on both sides").

## 1. What a passive observer sees today

### 1.1 The invite code is an IP disclosure

The app builds one `RTCPeerConnection` with only Google STUN configured (lines 442 to 445), creates one ordered data channel (line 755), gathers fully before producing the code (lines 687 to 704), then gzips and base64s the SDP (lines 722 to 730). [UNVERIFIED, flagged by the stage review, no artifact backs this sample, R3 must re-derive the live run:] A real Chromium run on 2026-11-26 produced a 660 character code that decoded to 716 characters of SDP. Redacted for this document, structure preserved:

```
v=0
o=- 269254974551727727 2 IN IP4 127.0.0.1
s=-
t=0 0
a=group:BUNDLE 0
a=extmap-allow-mixed
a=msid-semantic: WMS
m=application 63503 UDP/DTLS/SCTP webrtc-datachannel
c=IN IP4 77.71.x.x
a=candidate:2997885883 1 udp 2113937151 455d707c-54a5-4e4d-9009-496947b959bc.local 63503 typ host generation 0 network-cost 999
a=candidate:483261659 1 udp 1677729535 77.71.x.x 63503 typ srflx raddr 0.0.0.0 rport 0 generation 0 network-cost 999
a=ice-ufrag:YGVv
a=ice-pwd:VQ/4Sy/JVYLcoMI5LhzmhckC
a=ice-options:trickle
a=fingerprint:sha-256 71:5E:A1:71:E6:65:D4:E5:1C:99:FA:D9:81:28:F5:D2:62:67:9C:76:5F:34:C8:4B:FA:09:D0:27:28:2A:17:F1
a=setup:actpass
a=mid:0
a=sctp-port:5000
a=max-message-size:262144
```

Four facts follow directly.

1. The public IP and the exact UDP port are in the code, in the `c=` line and in the srflx candidate. The mDNS host candidate protects the LAN address, not the public one. Whoever sees the invite, including O3 and any mail or chat provider on the path, learns where the offerer is and which port to knock on.
2. The mDNS host candidate (`*.local`) confirms the browser is applying local-IP concealment, the mechanism specified in draft-ietf-rtcweb-mdns-ice-candidates-04 (https://datatracker.ietf.org/doc/html/draft-ietf-rtcweb-mdns-ice-candidates-04, "concealing IP addresses with dynamically generated Multicast DNS (mDNS) names"). That protection is real but narrow.
3. `a=ice-options:trickle` is advertised even though the app delivers candidates in one blob after gathering completes (lines 687 to 704, 761, 792). The session is non-trickle in practice. The attribute is a leftover from the browser default and should not be read as a live trickle channel.
4. `a=setup:actpass`, `a=sctp-port:5000` and `a=max-message-size:262144` are stock Chromium values. They add nothing secret, and they are the same on every instance of this app, which matters for fingerprinting in 1.3.

### 1.2 Wire-level view per observer

| Observer | What is visible | What is not |
|---|---|---|
| O1 | UDP flow between two ephemeral ports, STUN binding requests every 30 s or less, a DTLS handshake, then DTLS records carrying SCTP | Payload. DTLS application data is encrypted |
| O2 | The same, plus the ability to classify it as WebRTC and drop it with one rule | Payload. DTLS application data is encrypted |
| O3 | The SDP, so both public IPs, both ports, both ICE passwords, both DTLS fingerprints | Nothing else. It does not see the session |
| O4 (Google STUN) | Source IP, timing, and the fact that this client is doing WebRTC | The peer identity and the content |
| O5 | Your public IP, your port, your timing, and your volume | Content |

The protocol multiplexing is standard. In WebRTC, STUN, TURN, DTLS and, for media sessions, SRTP can share one UDP port and are demultiplexed on the first byte (https://www.rfc-editor.org/rfc/rfc7983.html, which updates the scheme defined for DTLS-SRTP). That is what makes the flow cheap to classify.

### 1.3 Fingerprintability: the tells

The transport is unlinkable to a service but trivially identifiable as a protocol. Both halves matter.

- No name on the wire. A data channel has no SNI and no HTTP Host. There is nothing to whitelist and nothing to attribute. An observer cannot say which product this is, only what protocol family it belongs to.
- First-byte demux. The first byte has non-overlapping values for STUN, DTLS, TURN channel data and RTP, so a classifier can pick the protocol from one byte (RFC 7983). One rule separates this flow from QUIC, DNS and ordinary UDP.
- DTLS handshake shape. ClientHello, ServerHello, Certificate, Finished, with browser-specific cipher suite and extension ordering. That is exactly what JA3 and its successor JA4 fingerprint (https://github.com/FoxIO-LLC/ja4, "a suite of network fingerprinting methods"). A DTLS ClientHello from a given Chromium build is a stable identifier for browser family and often version.
- Certificate exposure depends on version. Under DTLS 1.2 the handshake, including the self-signed certificate, is in the clear until ChangeCipherSpec (https://www.rfc-editor.org/rfc/rfc6347.html). Under DTLS 1.3 everything after ServerHello is encrypted, and the cookie extension replaces HelloVerifyRequest (https://www.rfc-editor.org/rfc/rfc9147.html). The SDP carries no DTLS version attribute, so the code cannot tell you which will be negotiated. Treat the certificate as potentially visible to O1.
- Timing. Consent freshness requires a valid STUN binding exchange at least every 30 seconds, and the endpoint MUST stop transmitting if consent expires (https://www.rfc-editor.org/rfc/rfc7675.html). That yields a steady keepalive cadence for the life of the session, including idle periods.
- Size profile. Text messages are small DTLS records. File transfer is 16 KB application chunks (lines 428, 913 to 915) inside DTLS records, sent back to back at line rate. A long run of near-16 KB datagrams in one direction, with small ACK-like traffic in the other, is a file transfer to any observer who cares to look.

Verdict for the current build. Undetectability against O1 and O2 is zero. The flow is not merely detectable, it is anomalous, because two browsers opening a direct high-rate UDP session with no server is rare on most networks. The cost to block it is one firewall rule, for example drop non-QUIC UDP above 1024 bytes. The content is protected, the fact of communication is not, and the peer addresses are not.

### 1.4 What is actually protected

Content is protected properly. DTLS with a self-signed certificate whose fingerprint is bound into the SDP gives integrity and confidentiality, and the fingerprint is the identity binding the security architecture relies on (https://www.rfc-editor.org/rfc/rfc8827.html, on binding the communication to a key pair via the `fingerprint` attribute). A passive observer cannot read or modify the channel. An active attacker who controls the signaling channel can substitute both codes and sit in the middle, which is why 1.1 matters and why section 7 recommends an out-of-band short authentication string even in the no-infrastructure variant.

Metadata is not protected. The WebRTC security model says so plainly: "as soon as the callee sends their ICE candidates, the caller learns the callee's IP addresses. The callee's server-reflexive address reveals a lot of information about the callee's location ... either side may wish to hide their location from the other side entirely by forcing all traffic through a TURN server" (https://www.rfc-editor.org/rfc/rfc8826.html, section 4.2.4). The app does the opposite of hiding: it puts the address in a copyable string.

## 2. Hiding peer IPs from each other and from observers

There are only three real mechanisms. Conceal the local address, relay the traffic, or move the transport off IP entirely. Concealing the local address is already done by the browser and does not touch the public one. Relaying is TURN. Moving off IP is Tor.

### 2.1 Force relay through a private TURN server `[INFRA]`

Mechanism. Run coturn (https://github.com/coturn/coturn, "a free open source implementation of TURN and STUN Server") and set `iceTransportPolicy: "relay"`. The W3C specification defines `relay` as using "only media relay candidates such as candidates passing through a TURN server", against a default of `all` (https://w3c.github.io/webrtc-pc/). With relay forced, the SDP contains relay candidates only. No host candidate, no server-reflexive candidate, no public IP, and no LAN mDNS name.

Observer effect.
- O3 (signaling observer) sees a TURN address and port, not the peer's address.
- O5 (peer) sees the relay, not you.
- O1 sees two flows to the relay instead of one flow between peers. It still sees volume and timing, and it can still classify WebRTC if the client speaks TURN over UDP.
- O4 (relay operator) sees both source IPs, both session lifetimes, and the full volume. If you run the relay, the hosting provider becomes O4 and you become a metadata holder for your users. That is a real change in trust position, not a cosmetic one.

Cost. Every byte crosses the relay twice. A 50 MB file becomes 100 MB of relay egress. A small VPS with 1 TB of monthly transfer carries roughly 10,000 such transfers before overage, assuming nothing else shares the box (inferred arithmetic, not a provider claim). Latency rises by the relay detour, typically tens of milliseconds (estimate, not measured here). The relay also needs credentials. Use short-lived TURN REST credentials rather than a static user and password, because a static credential turns the relay into an open proxy for anyone who reads the config.

What it does not fix. The relay itself is a visible, blockable endpoint. If the relay is on a residential or small-provider IP, it is a single point of failure for availability and a single point of seizure for metadata.

### 2.2 TURN over TLS on 443 `[INFRA]`

Mechanism. Use `turns:` instead of `turn:`. RFC 8656 defines TURN over TLS and DTLS with a default port of 5349 (https://www.rfc-editor.org/rfc/rfc8656.html), but nothing stops an operator from listening on 443. Then the flow is TLS to one host, and O2 cannot block it as "UDP that is not QUIC" or as port 3478 without also blocking ordinary HTTPS.

Observer effect. Defeats O2 port and protocol blocking. Defeats O1 protocol classification only until it looks at the destination, because a long-lived TLS connection carrying sustained bidirectional high-bitrate data is not normal HTTPS. The SNI of the relay domain is visible unless ECH is in play, and the domain is a durable blocklist entry. Use a bland, unmemorable name, and do not reuse the app's brand on it.

Cost. TLS adds handshake and record overhead, modest compared to the relay cost. coturn needs a certificate and renewal. This is the single highest-value infrastructure upgrade in this document, because it hides peer IPs and survives UDP filtering at the same time.

### 2.3 VPN on both ends `[INFRA, third party]`

Mechanism. Both peers connect through VPNs before generating codes. The srflx candidate becomes the VPN egress address, and host candidates remain mDNS names. The peers then see VPN addresses. RFC 8828 covers the browser requirements for IP handling in this situation (https://www.rfc-editor.org/rfc/rfc8828.html, "WebRTC IP Address Handling Requirements").

Observer effect. Defeats O5 and O3 address disclosure if the VPN is honest and does not leak. Does not defeat O1 classification. If both peers use the same commercial VPN, that provider sees both ends and is a better-positioned O4 than any TURN server you could run. If the VPN is blocked, the app does not connect.

Cost. No new infrastructure of yours, but a standing dependency on a third party for every session. It also does not compose with the "static single file" promise, because it requires user configuration outside the app.

### 2.4 Tor onion service as the transport, no relay of yours

Mechanism. Each side publishes a v3 onion service and connects to the other's onion address instead of exchanging IP candidates. Onion services hide location by design: "An Onion Service's IP address is protected. Onion services are an overlay network on top of TCP/IP, so in some sense IP addresses are not even meaningful to Onion Services: they are not even used in the protocol" (https://community.torproject.org/onion-services/overview/).

Observer effect. Defeats O3, O5 and O1 address disclosure completely. The invite code contains a `.onion` name. O1 sees Tor traffic, not a peer address. O5 sees the onion, not your IP. O2 can only block Tor as a category. O4 becomes the Tor network, which is many operators rather than one.

Cost. Latency and throughput. A 50 MB file over Tor is slow and may fail on a mobile link. Tor is blocked on some networks and needs bridges. The browser cannot open a raw onion socket, so this option is not a static HTML file at all. It is a different application.

### 2.5 Summary

| Option | O1 address | O2 block | O3 code | O5 peer | INFRA | New trusted party |
|---|---|---|---|---|---|---|
| Current build | sees both | one rule | full IP and port | full IP | no | Google STUN |
| mDNS only | sees public IP | one rule | public IP | public IP | no | Google STUN |
| TURN relay, UDP | sees relay only | blocks 3478 | relay only | relay only | yes | you or the relay host |
| TURN over TLS 443 | sees TLS to relay | much harder | relay only | relay only | yes | you or the relay host |
| VPN both ends | sees VPN egress | depends | VPN IP | VPN IP | yes, third party | the VPN |
| Tor onion | sees Tor | blocks Tor | onion only | onion only | no, but Tor network | Tor directory and guards |

What does not work, so nobody spends a sprint on it. Editing the IP out of the SDP breaks ICE, because a candidate has to be reachable. Setting `iceTransportPolicy` to `relay` without a relay produces no candidates and no connection. Turning off STUN entirely gives host candidates only, which fails across NAT and still exposes the LAN to the peer when mDNS is unavailable.

## 3. Undetectability options, ranked per observer

Ranking depends on which observer you care about. Five options are assessed, then ranked three ways.

### 3.1 Private TURN over TLS on 443 `[INFRA]`

Defeats. O3 and O5 address disclosure. O2 port and protocol blocking. Against O1 it defeats protocol classification only at the first hop, because the destination is a TLS server and the flow profile is unusual.

Tells. SNI of the relay domain, certificate chain, a single long-lived TLS connection with sustained high bitrate, and TURN channel data inside TLS if the relay does not pad. Traffic volume during a file transfer is a near-perfect signal that something bulk is happening, even if the content is opaque.

Verdict. Best availability-per-effort. Not stealth against a determined classifier, but it removes the two worst exposures (peer IPs and UDP blocking) with one server and one config flag.

### 3.2 WebSocket over TLS with domain fronting, status in 2026 `[INFRA]`

Mechanism. Carry the session over a WebSocket to a CDN edge, with the TLS SNI naming a high-reputation front domain and the HTTP Host header naming the real origin. Classic domain fronting is exactly that mismatch on shared CDN infrastructure (https://arxiv.org/abs/2310.17851, "Measuring CDNs susceptible to Domain Fronting").

Status. The big clouds closed the easy versions. Google and Amazon disabled domain fronting in 2018, and Azure disabled it for resources created after 8 November 2022 with enforcement for existing domains from 22 January 2024, failing with HTTP 421 and the log marker `SSLMismatchedSNI` (https://routeharden.com/blog/domain-fronting-2026, which quotes the Azure Front Door FAQ at https://learn.microsoft.com/en-us/azure/frontdoor/front-door-faq). The same 2026 survey's own conclusion is in its title: "mostly dead, not actually gone". It survives on smaller CDNs and misconfigured edges, not as a dependable design input.

ECH is not domain fronting. With Encrypted Client Hello, every ECH-enabled site on Cloudflare shares the outer name `cloudflare-ech.com`, so an observer sees Cloudflare but not which site (https://developers.cloudflare.com/ssl/edge-certificates/ech/). That defeats SNI-based blocking of your specific domain. It does not hide the fact that the connection terminates at Cloudflare, and Cloudflare still sees the origin. For a two-person chat it also means the CDN is a standing O4 with the full connection graph.

Verdict for 2026. Do not make classic domain fronting a primary plan. If a CDN is acceptable, ECH plus a WebSocket to a CDN-hosted origin is the supportable version, and its value is hiding the site name from O1/O2, not hiding the traffic.

### 3.3 Traffic morphing in the v2ray and shadowsocks style `[INFRA]`

Mechanism. Two families. Shadowsocks is an encrypted proxy with AEAD ciphers, including the 2022 ciphers selected through SIP022 (https://github.com/shadowsocks/shadowsocks-rust, which exposes `aead-cipher-2022`). It produces a random-looking byte stream and relies on looking like nothing in particular. v2ray and Xray go further with TLS mimicry. VLESS with REALITY is "a modified form of TLS that uses the appearance and handshake characteristics of a target site as camouflage" (https://xtls.github.io/en/config/transports/reality.html), configured with a `target` and `serverNames` that name a real site whose identity the server borrows (https://github.com/XTLS/REALITY/blob/main/README.en.md).

Defeats. O2 fingerprinting and active probing, because a prober without the secret gets a handshake consistent with the target site rather than a self-signed WebRTC certificate. Also defeats SNI-based blocking of your own domain, since your domain never appears. Against O1 it defeats protocol classification, because the flow is TLS to a plausible site.

Tells. The destination IP and its reputation, the certificate of the borrowed site (valid but not yours), flow timing that does not match browsing, and the fact that a long-lived TLS session with continuous high bitrate is not how a website behaves. Statistical classifiers do not need to break TLS to flag that.

Verdict. Strongest practical DPI resistance available to a small team, and the highest operational burden. You now run a proxy server with a real domain name, a fallback site, and a reason for existing. It concentrates all metadata in one endpoint that you own. Marked `[INFRA]` for a reason.

### 3.4 WireGuard as an alternate tunnel mode `[INFRA]`

Mechanism. Both peers join a WireGuard network, and the WebRTC session runs inside the tunnel. WireGuard is simple, fast and well understood (https://www.wireguard.com/protocol/).

Undetectability. Effectively none on its own. WireGuard has distinctive packet signatures, which is why AmneziaWG exists: "The precursor, WireGuard, is known for its efficiency but had issues with detection due to its distinctive packet signatures" (https://github.com/amnezia-vpn/amneziawg-go). A single UDP port that only speaks WireGuard is itself a tell. If WireGuard is the transport, wrap it in AmneziaWG or run it over TLS.

What it is good for. Hiding peer IPs from each other with less per-byte cost than TURN, and giving both peers a stable private address for a hosted entry (section 6). It is a network-layer answer, not a stealth answer.

### 3.5 Tor onion services and prior art `[INFRA: Tor network, no host of yours]`

Mechanism. Two onion services connect to each other. No IP, no port, no DNS, end-to-end encryption and NAT punching are properties of the design (https://community.torproject.org/onion-services/overview/).

Prior art, all three solve the same problem and all three are worth reading before building anything:
- Cwtch. "All communication in Cwtch is end-to-end encrypted and takes place over Tor v3 onion services ... designed such that no information is exchanged or available to anyone without their explicit consent, including on-the-wire messages and protocol metadata" (https://docs.cwtch.im/security/intro).
- Ricochet Refresh. A peer-to-peer messenger over Tor onion services, "Metadata Resistant", "None of your contacts know your location or IP address", "There are no servers to trust, monitor, or hack", with native file transfer (https://ricochetrefresh.net/).
- Briar. Syncs directly between devices over Tor when the internet is up, and over Bluetooth or Wi-Fi when it is not, specifically against metadata surveillance (https://briarproject.org/how-it-works/).

Defeats. O1 and O2 address and protocol attribution, O3 and O5 address disclosure. O2 can still block Tor as a category, and in a network that blocks Tor the option is unavailable without bridges. O6 remains out of scope by Tor's own statement (cited in the method section).

Cost. Latency, throughput, and a hard dependency on the Tor network being reachable. For a 50 MB file this is the worst option on user experience and the best on metadata.

### 3.6 Rankings

Ranked for undetectability against an active DPI adversary, strongest first:

1. REALITY-style TLS morphing `[INFRA]`. Beats O1 and O2 classification, survives active probing.
2. Tor onion services. Beats O1 and O2 attribution entirely, loses if Tor is blocked.
3. ECH plus CDN-hosted WebSocket `[INFRA]`. Hides the site name, leaves the CDN visible.
4. TURN over TLS on 443 `[INFRA]`. Looks like HTTPS until the flow profile is examined.
5. WireGuard `[INFRA]`. Detectable by signature without a wrapper.
6. Current build. Zero.

Ranked for hiding peer IPs from each other, strongest first:

1. Tor onion. No IP in the protocol.
2. TURN with relay forced `[INFRA]`. Peer sees the relay only.
3. VPN on both ends `[INFRA, third party]`. Peer sees the VPN egress.
4. Current build. Peer sees the public IP in the invite code.

Ranked by operational burden, cheapest first: current build, then TURN `[INFRA]`, then WireGuard `[INFRA]`, then Tor, then REALITY `[INFRA]`. Every step up in stealth adds a host that must stay up, or a network that must stay reachable.

## 4. Inbound gating for a serverless app

The current design already has a strong default deny, by accident of architecture. It is worth naming the layers because most proposed additions are already there, and the ones that are missing cannot be fixed in the app.

### 4.1 The chain, in order

1. No listener exists at rest. A static file opens no socket. The UDP socket appears only when `setLocalDescription` starts gathering (lines 756 and 757, 789 and 790). Close the peer and the socket goes away (lines 541 to 552, which close the channel and the peer connection).
2. The 5-tuple is not discoverable. The OS picks an ephemeral port, observed as 63503 in the probe. The only place it is published is the SDP, which is the invite or reply code.
3. ICE credential gate. Connectivity checks use STUN short-term credentials. RFC 8445 requires that the values be unguessable, with "at least 128 bits of random number generator output used to generate the password, and at least 24 bits of output to generate the username fragment" (https://www.rfc-editor.org/rfc/rfc8445.html, section 5.3). The observed code matches the shape: a 4 character ufrag and a 24 character password. A binding request without a valid MESSAGE-INTEGRITY over that password fails the credential check and is not answered. A forged binding response is discarded for the same reason, which RFC 8445 states explicitly in its security considerations: "in order for this response to be processed, the attacker needs the password".
4. DTLS gate. A ClientHello from an unknown source gets no handshake state. DTLS 1.2 answers with a stateless HelloVerifyRequest carrying a cookie (https://www.rfc-editor.org/rfc/rfc6347.html), and DTLS 1.3 uses the cookie extension and notes it is "an important DoS prevention mechanism for UDP-based protocols" (https://www.rfc-editor.org/rfc/rfc9147.html). Until the cookie comes back, the server holds nothing.
5. Certificate gate. The handshake only completes against the certificate whose fingerprint is in the SDP. A party without the private key fails at Finished. The fingerprint binding is the WebRTC identity mechanism (https://www.rfc-editor.org/rfc/rfc8827.html).
6. SCTP gate. SCTP runs inside DTLS (https://www.rfc-editor.org/rfc/rfc8261.html, "DTLS Encapsulation of SCTP Packets"). There is no SCTP association to attack before DTLS completes.
7. Data channel gate. The channel is established with DCEP over the SCTP association (https://www.rfc-editor.org/rfc/rfc8832.html). No association, no channel, no application parser.
8. Consent freshness. Once established, consent expires after 30 seconds and the endpoint MUST stop transmitting if a valid binding exchange has not happened (https://www.rfc-editor.org/rfc/rfc7675.html). The browser implements this, so the app inherits it for free. It bounds how long a stale or spoofed path can keep receiving.

### 4.2 What an uninvited packet can and cannot do today

| Packet | Result | Residual risk |
|---|---|---|
| UDP datagram to a random high port | No socket, or an ICMP unreachable if the host replies at all | Port scanning 2^16 ports is cheap, but the socket exists only during a session |
| STUN binding request to the right port, no credentials | Discarded, no response | None beyond confirming the port is live if a response were sent, which it is not |
| STUN request with the ufrag but a wrong password | Discarded | The ufrag is only 24 bits, but it is useless without the password |
| STUN request with correct credentials, from an unknown address | Accepted, and may create a peer-reflexive candidate | This is ICE working as designed. It requires the code |
| DTLS ClientHello to the right port | HelloVerifyRequest or cookie only, no state, no certificate under 1.3 | Confirms a DTLS endpoint exists. Does not confirm the app |
| DTLS with a valid cookie, wrong certificate | Handshake fails at Finished | CPU cost per attempt, bounded by the cookie |
| SCTP INIT without DTLS | Impossible, SCTP is inside DTLS | None |
| DCEP OPEN without SCTP | Impossible | None |
| Application message without a channel | Impossible | None |
| Holder of the invite code | Can complete ICE and DTLS and become the peer | This is the design. The code is a bearer capability |

Two honest conclusions. First, the pre-auth surface is about as small as an internet-facing UDP service can get, because four protocol layers must agree before any application code runs. Second, the gate is a secret, not a proof of intent. Anyone who sees the code is invited. There is no notion of "uninvited but authenticated" and no way to revoke a leaked code except to wipe and re-pair.

Amplification is negligible. A STUN binding response is about the size of the request, and a HelloVerifyRequest is smaller than the ClientHello that triggers it. This is not a reflection amplifier, and it should not be treated as one in the threat model.

### 4.3 Pairing code entropy math

The current code is 660 characters and is not guessable. The question matters for any future short code, for example a six-word phrase or a nine-digit PIN that a user reads aloud. The math below is for a full sweep of the space. Expected work is half of that.

| Secret | Entropy | Full sweep at 1e6 guesses/s | Full sweep at 1e9 guesses/s |
|---|---|---|---|
| 6 EFF words (7776 word list) | 77.5 bits | 3.5e9 years | 3.5e6 years |
| 4 EFF words | 51.7 bits | 58 years | 21 days |
| 8 base32 characters | 40 bits | 6.4 days | 9.2 minutes |
| 9 decimal digits | 29.9 bits | 8.3 minutes | 0.5 seconds |
| ICE password, 128 bits | 128 bits | infeasible | infeasible |

Online guessing is much slower than the right column, because each attempt costs a network round trip and a failed handshake, so single-digit to low tens of attempts per second per connection. A botnet multiplies that. That is why the offline column is the one that matters: assume the attacker captures one verifier and grinds it locally. Four words at 21 days on a fast rig is not enough for a long-lived pairing secret. Six words at 77.5 bits is enough with margin. Nine digits is not a security boundary at all.

If a short code is ever introduced, pair it with a password-authenticated key exchange so that no offline verifier exists. SPAKE2 is specified for exactly this case, two parties sharing a weak password deriving a strong key without disclosing the password (https://www.rfc-editor.org/rfc/rfc9382.html). A short code without a PAKE is a 30-bit secret with a friendly face.

### 4.4 Application-layer rate limiting and puzzles, honestly

The app cannot rate limit before authentication in any meaningful way. The expensive pre-auth work happens inside the browser's DTLS and ICE stacks, below the JavaScript. A token bucket keyed by source IP is spoofable and shared behind NAT. A token bucket keyed by ICE ufrag requires the secret, at which point the caller is already invited. So the pre-auth rate limiter is the DTLS cookie, and it is already there.

A proof-of-work puzzle has the same placement problem. The server cannot demand a puzzle before the ClientHello, because the ClientHello is handled by the browser. Embedding a puzzle in the invite code moves the cost to the answerer and gates only the answer-acceptance step, which is a nuisance filter for a spammed signaling channel, not a DDoS defense.

What is worth building is post-auth rate limiting, because the peer is authenticated but not trusted:
- messages per second and bytes per second per session,
- one file transfer in flight at a time (line 999 already enforces one incoming transfer, by rejecting a second `file-start`),
- a cap on session total bytes,
- a cap on log rows and on retained blob URLs.

That is cheap and it bounds the damage a malicious peer can do to the tab, which is the only resource a serverless design has to protect.

## 5. What a swarm attacker can even target without a server

A distributed attacker needs a destination that is always up, enumerable, and shared. This design has none of those. There is no endpoint to flood, no directory to scrape, and no session identifier to guess. That is the strongest property of the architecture and it should be stated in the product material without hedging.

What remains targetable is three things.

### 5.1 The STUN dependency

This is the only always-on third party in the request path. `stun.l.google.com:19302` and `stun1.l.google.com:19302` (lines 442 to 445) are the sole source of server-reflexive candidates. Consequences:

- Blocking those names, by DNS or by IP, removes every srflx candidate. The session then has host candidates only and fails across any NAT. The failure mode is a generic "Could not connect" (line 650), which is indistinguishable from a peer problem.
- Google sees the source IP, the timing, and the fact that this client is gathering WebRTC candidates (O4). It does not see the peer.
- A single provider is a single point of blocking and a single point of surveillance. Three independent STUN providers, tried in order, with the chosen one recorded in the code, would remove the single point. It costs a few lines and no infrastructure.

### 5.2 The signaling path

The codes are the only capability. An attacker who can read the channel gets both IPs, both ports, both ICE passwords and both fingerprints, and can attempt to be the peer. An attacker who can write the channel can substitute codes and sit in the middle. The app accepts whatever answer is pasted (line 815) and relies on DTLS to reject a wrong fingerprint, so a substitution produces a failed connection rather than a silent compromise. That is fail closed on integrity, but it is a denial of service and it is invisible to the user, who sees only "connection failed".

The fix is an out-of-band short authentication string: derive four words from the two DTLS fingerprints in sorted order and ask both users to compare them. A signaling MITM cannot produce matching words without breaking the hash. This is the single highest-value no-infrastructure hardening in this document.

A swarm can also spam the signaling channel, race to answer first, or flood one side with fake answers. Each fake answer costs a paste and a failed handshake. Rate limiting the paste action and showing the SAS turns that from a nuisance into a visible event.

### 5.3 The peer browser

After authentication, the peer controls the application protocol. Three concrete resource issues in the current build:

- Declared file size is allocated eagerly. `beginIncoming` does `new Uint8Array(size)` for any size up to 50 MB as soon as a `file-start` message arrives (lines 998 to 1017, allocation at 1011). No bytes need to follow. One transfer at a time is enforced (line 999), so the ceiling is 50 MB held indefinitely, until the 30 minute idle wipe or a manual wipe. A lazy or chunked buffer, plus a timeout on a transfer that makes no progress, removes it.
- Blob URLs accumulate for the life of the session. Each sent or received file pushes a URL into `urls` (lines 891, 1048) and they are revoked only at `endSession` (lines 559 to 561). Ten 50 MB files pin 500 MB until wipe. Revoking on save or after a small ring of recent files bounds it.
- The message log has no row cap. Every message appends a DOM node (lines 523, 536, 967). Text is capped at 20 KB per message (lines 429, 830), but the count is unbounded. A peer sending small messages at line rate grows the DOM until the tab slows or crashes.

None of these is a remote code execution risk. All of them are trivial for a malicious peer and all of them are cheap to bound. They matter more than usual here because there is no server-side quota to fall back on. The tab is the whole system.

## 6. Default deny for a possible future hosted entry

If a hosted entry ever exists, it inverts the risk. Today the attacker must find a secret. With a hosted endpoint, the attacker can find the endpoint by scanning and attack it continuously. The design rule is that the entry is a door, not a lobby: nothing answers, and no TCP listener exists, until the caller proves possession of a key.

### 6.1 Single packet authorization with fwknop `[INFRA]`

Mechanism. fwknop implements SPA. The client sends one encrypted, authenticated UDP packet. The server verifies it, checks it against a replay cache, and only then opens the firewall for that source address for a short window. The design goals are explicit: the packet must be encrypted, and "even if the attacker is unsuccessful in decoding them, it should not be possible for the attacker to replay captured messages against the knock server" (https://cipherdyne.org/fwknop/docs/SPA.html).

Why it fits. To a scanner, the host has no open ports. A captured packet cannot be replayed. Authorization is per source address, so the opened window is useless to anyone else. It reduces scan noise and opportunistic exploitation to near zero, and it costs one small daemon and an nftables rule.

What it is not. SPA is not application authorization. It only decides whether a packet reaches the TLS listener. The session still needs its own authentication and its own per-identity limits, and the SPA key must be distributed out of band, which is the same problem as the pairing code at one remove.

### 6.2 A WireGuard-only door `[INFRA]`

Mechanism. The host exposes no TCP at all. The only listening socket is UDP WireGuard. The application binds to the tunnel address, so it is unreachable from the internet even if it has a bug.

Strengths. Mutual key authentication before any application bytes. No scanner-visible service. No certificate chain to misconfigure. Revocation is a key removal.

Weaknesses. WireGuard is fingerprintable, and a host whose only open port speaks WireGuard is itself a signal, which is why AmneziaWG exists (https://github.com/amnezia-vpn/amneziawg-go). Every client needs a config file, which is a worse onboarding story than a URL. And the tunnel operator sees both ends, so it becomes O4 in the same way a TURN relay does.

Choice between 6.1 and 6.2. SPA if the entry must speak ordinary TLS to ordinary browsers. WireGuard if the clients can be configured once and the entry is for a known group. SPA is the better fit for a two-person product with a link-based invite.

### 6.3 Per-identity limits

Rate limit by identity, not by IP. IP is shared behind NAT and spoofable. The identity is the pairing public key or its hash.

- One active session per pairing key. A second attempt evicts the first or is refused, and the choice must be explicit.
- N new sessions per key per hour, and M per source IP per hour as a coarse backstop.
- A global concurrency cap, so a flood cannot exhaust file descriptors or memory.
- A CPU budget per handshake, and a queue with a hard depth.
- Fail closed. If the limiter, the key store, or the auth check is unavailable, refuse the connection. A fail-open path turns one outage into a breach.

### 6.4 Metadata minimization at the entry

The hosted entry is the one place where both peers and the timing concentrate. Log no source IPs. If abuse handling requires them, store a keyed hash with a rotating salt and a short retention, and say so in the product text. Never log message content, file names, or sizes. The relay already learns volume and timing. Do not build a second, richer record of the same session.

## 7. Ranked recommendations

Two variants, because the form-factor decision is the real fork. Each item states the observer it addresses and whether it adds infrastructure.

### 7.1 Variant A, strict no infrastructure

The constraint is a static file and two browsers. Under that constraint the product cannot hide IPs from the peers and cannot be undetectable on the wire. Say so in the UI instead of implying otherwise.

1. Short authentication string from both DTLS fingerprints. Show four words derived from the sorted pair of fingerprints, and ask both users to compare them out of band. Defeats O3 substitution and MITM. No `[INFRA]`. Highest value item in the whole document per line of code.
2. STUN diversity. Configure three independent STUN providers, try them in order, and surface a specific error when only host candidates are available. Defeats a single-provider block and reduces O4 concentration. No `[INFRA]`.
3. Post-auth resource caps: lazy file buffer with a progress timeout, per-file blob revocation, a log row cap, and message and byte rate limits per session. Defeats peer-driven tab exhaustion. No `[INFRA]`.
4. Honest disclosure. The invite code contains the public IP and port. Tell the user, and tell them a VPN changes it. Do not claim anonymity. No `[INFRA]`.
5. If a short code is ever added, six EFF words plus SPAKE2 (RFC 9382). No `[INFRA]`.
6. Keep the existing default deny as is. Non-trickle ICE, DTLS, SCTP, DCEP and 30 second consent freshness are already the correct chain. Do not add a pre-auth puzzle; it has nowhere to run.

Residual risk accepted by variant A: O1 and O2 can classify and block the flow with one rule. O3 and O5 see the public IP. O6 is out of scope. The mitigation is user-side VPN or Tor, documented, not built.

### 7.2 Variant B, infrastructure allowed

The constraint is relaxed to one small host, and the ranking changes.

1. Private TURN with `iceTransportPolicy: "relay"`, listening as `turns:` on 443, with short-lived credentials. Defeats O3 and O5 address disclosure, and O2 port and protocol blocking. `[INFRA]`. This is the first thing to build and the only change that fixes the invite-code IP leak.
2. Signaling over TLS to the same host, plus the SAS from A1. Defeats O3. `[INFRA]`. Keeping signaling on the same domain as the relay avoids a second fingerprint and a second certificate.
3. Hosted entry behind fwknop SPA, with per-identity limits and fail-closed behavior. Defeats scanning and opportunistic exploitation. `[INFRA]`. Use a WireGuard-only door instead if every client can be configured once.
4. If DPI resistance is a stated requirement, put REALITY in front of the TLS endpoint. `[INFRA]`. Second choice is ECH plus a CDN-hosted WebSocket. Classic domain fronting is not a plan in 2026; the big clouds closed it and the survivors are unreliable.
5. Tor onion transport only if the threat model includes the relay operator and O1 attribution. It is the strongest metadata answer and the worst file-transfer experience. Borrow the design from Cwtch, Ricochet Refresh and Briar rather than inventing a new onion protocol. `[INFRA: Tor network, no host of yours]`.
6. WireGuard as a transport only with an obfuscation wrapper. Plain WireGuard is a network convenience, not a stealth layer. `[INFRA]`.

### 7.3 What not to build

- A pre-auth proof-of-work puzzle. It cannot run below the browser's DTLS stack, so it gates nothing an attacker cares about.
- Classic domain fronting as a primary transport in 2026. The reliable fronting era ended between 2018 and 2024.
- Plain WireGuard sold as undetectable. Its own ecosystem ships a fork to fix the signature.
- SDP rewriting to remove addresses. It breaks ICE and hides nothing that matters, because the srflx candidate is the leak.
- A custom pairing protocol. Use SPAKE2 if a short code is needed. Do not roll a new PAKE.

## SELF-CHECK

Acceptance items from the lane brief, with evidence.

1. Every option states its observer model. PASS. Sections 2.1 to 2.4 each list O1, O2, O3, O5 and O4 where applicable. Section 3.1 to 3.5 each state what is defeated and what is told. Section 6.1 and 6.2 state the scanner and operator views. Section 7 items name the observer per item.
2. Every option that needs standing infrastructure carries `[INFRA]`. PASS. Tagged: TURN relay, TURN over TLS, VPN, REALITY, ECH plus CDN, WireGuard, fwknop, hosted entry. Untagged and explicitly no-infrastructure: mDNS, SAS, STUN diversity, Tor onion (tagged as Tor network dependency, no host of yours), client-side caps.
3. External claims carry verified URLs. PASS. Fetched and title-checked during this run: rfc8445, rfc7675, rfc7983, rfc8261, rfc8832, rfc8826, rfc8827, rfc8828, rfc6347, rfc8656, rfc9147, rfc9382, draft-ietf-rtcweb-mdns-ice-candidates-04, w3c.github.io/webrtc-pc, github.com/FoxIO-LLC/ja4, github.com/coturn/coturn, github.com/XTLS/REALITY, xtls.github.io REALITY, github.com/shadowsocks/shadowsocks-rust, github.com/amnezia-vpn/amneziawg-go, wireguard.com/protocol, docs.cwtch.im/security/intro, ricochetrefresh.net, briarproject.org/how-it-works, community.torproject.org/onion-services/overview, blog.torproject.org traffic correlation summary, cipherdyne.org/fwknop/docs/SPA.html, arxiv.org/abs/2310.17851, routeharden.com domain fronting 2026, learn.microsoft.com Azure Front Door FAQ, developers.cloudflare.com ECH.
4. The file ends with a ranked recommendation set for two variants. PASS. Section 7.1 is strict no infrastructure, section 7.2 is infrastructure allowed, both ordered by priority with observer and INFRA per item.
5. No em dashes or en dashes. PASS. Checked with grep for U+2014 and U+2013, zero matches.
6. Claims about the app carry file:line references. PASS. Lines 428, 429, 442 to 445, 523, 536, 541 to 552, 559 to 561, 650, 687 to 704, 722 to 730, 755, 756 and 757, 789 and 790, 815, 830, 857, 891, 913 to 915, 967, 998 to 1017, 1048.
7. Arithmetic and estimates are labeled. PASS. Relay cost and transfer count marked as inferred arithmetic. Latency marked as an estimate. Entropy table computed at 1e6 and 1e9 guesses per second, stated as full-space sweeps.
8. Unverified claims are marked. PASS. No external claim in the file lacks a fetched source. The only unverified element is the DTLS version that a given browser will negotiate, which is explicitly stated as unknown because the SDP carries no version.

STATUS: complete.

