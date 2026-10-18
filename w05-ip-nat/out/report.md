# Week 5 Task 2 · Address and DHCP report

All address values below are from the two Windows network collections saved in
`addresses.json`. The DHCP findings are from the live Wireshark-compatible
capture in `dhcp.pcapng`.

## Part A · Address study

### Network 1: wired Ethernet (2026-10-18)

- Interface: Realtek Ethernet; IPv4 address `211.46.209.31`, mask
  `255.255.255.0` (`/24`).
- Subnet range calculated by hand: network `211.46.209.0`, usable range
  `211.46.209.1`–`211.46.209.254`, broadcast `211.46.209.255`.
- Task 1 check: `network_range("211.46.209.0/24")` should return the same
  usable endpoints and broadcast address.
- Default gateway: `211.46.209.1`; it is inside the connected `/24` subnet,
  so the host can reach it directly on the local link.
- `211.46.209.31` is not RFC 1918 space or the `100.64.0.0/10` CGNAT-shared
  range; it is globally routable address space.
- Public address observed by ipify: `211.46.209.31`, matching the interface
  address. This is evidence that no address translation is visible between
  this interface and the public endpoint. It cannot rule out an upstream
  one-to-one translation beyond the observations available here.
- Windows reports DHCP enabled; lease obtained 11:19:27 and expires 13:19:30
  local time (about 2 hours). DHCP server shown by Windows: `222.118.178.36`.

### Network 2: Wi-Fi (2026-10-18)

- Interface address `192.168.0.254`, mask `255.255.255.0` (`/24`).
- Subnet range calculated by hand: network `192.168.0.0`, usable range
  `192.168.0.1`–`192.168.0.254`, broadcast `192.168.0.255`.
- Task 1 `network_range("192.168.0.0/24")` returned
  `192.168.0.1`, `192.168.0.254`, `192.168.0.255`.
- Default gateway and DHCP server: `192.168.0.1`, inside the local `/24`.
- `192.168.0.254` is RFC 1918 private space. ipify saw public address
  `211.46.209.5`, so at least one NAT translation lies between this interface
  and the public Internet.

## Part B · Compare two networks

| Network label | Interface address | Mask/prefix | Default gateway | Public address |
|---|---|---|---|---|
| Wired Ethernet | 211.46.209.31 | 255.255.255.0 (/24) | 211.46.209.1 | 211.46.209.31 |
| Wi-Fi | 192.168.0.254 | 255.255.255.0 (/24) | 192.168.0.1 | 211.46.209.5 |

- The public address changed from `211.46.209.31` to `211.46.209.5`.
  The two connections use different egress paths/addresses.
- The interface address changed from a globally routable Ethernet address to
  private Wi-Fi address `192.168.0.254`; the Wi-Fi router assigns a local
  address while the outside sees its translated public address.
- For Wi-Fi, the evidence establishes at least one NAT. To distinguish one
  NAT from two, inspect the router's WAN address: a public WAN address suggests
  one NAT at that router; a WAN address in RFC 1918 or `100.64.0.0/10` indicates
  an upstream private/CGNAT layer as well. The endpoint measurements alone do
  not reveal that WAN-side address, so they cannot prove the exact count.

## Part C · DHCP

- Capture source: live Wi-Fi capture in `out/dhcp.pcapng`.
- DHCP message types observed: Release (7), Discover (1), Offer (2), Request
  (3), Ack (5). Thus the full DORA exchange is present.
- Discover source: `0.0.0.0`; destination: `255.255.255.255`.
- Discover must use `0.0.0.0` because the client has not received an address
  yet; it broadcasts because it does not yet know the DHCP server's address.
- The Offer's option 51 lease time is **3,600 seconds (1 hour)**.
- In this capture the ACK was also broadcast to `255.255.255.255`. After the
  offer/request exchange, the server knows the selected client and offered
  address, so an ACK can be unicast when the client's broadcast flag and
  receive state permit it; this server chose broadcast for this exchange.
- At half the lease (T1 = **1,800 seconds / 30 minutes**), the client normally
  tries to renew with the original DHCP server using DHCPREQUEST, typically
  unicast.
