🏠 [Home](../../README.md) › 04 · Model Context Protocol (MCP)

# 04 · Model Context Protocol (MCP)

> **Estimated reading time:** ~64 min · **Difficulty:** 🟢 Beginner to 🔴 Advanced · **Prerequisites:** [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md)

In chapter 03 you gave an agent tools by writing them into your own code. That works until the same tool is needed in five apps, or you want to use tools someone else wrote. The Model Context Protocol (MCP) is the open standard that solves this: a system is wrapped once as an MCP server, and any AI app that speaks MCP can use it. This chapter explains why MCP exists, how its pieces fit together, how to build and test a server in Python, how to plug MCP tools into your own agent loop, and how to stay safe when the server isn't yours. Everything is written against the current specification (revision 2026-07-28) and the Python SDK 2.x (`mcp==2.3.0`).

## 🎯 What you'll learn

- The N × M integration problem, and how MCP turns it into N + M
- The three roles (host, client, server) and the two transports (stdio and Streamable HTTP)
- What changed in revision 2026-07-28: no `initialize` handshake, no sessions, optional `server/discover`
- The three server primitives and who controls each: tools (model), resources (application), prompts (user)
- How to build, test and run an MCP server with the Python SDK's `MCPServer`
- How to feed MCP tools into your own agent loop, and when to let Anthropic or OpenAI connect to a remote server for you
- The main MCP security risks (tool poisoning, prompt injection in results, rug pulls, confused deputy, token passthrough) and practical defences

## 📋 Prerequisites

- [3.1 What is a tool?](../03-tools-and-function-calling/03.1-what-is-a-tool.md), [3.2 JSON Schema for tools](../03-tools-and-function-calling/03.2-json-schema-for-tools.md) and [3.3 How function calling works](../03-tools-and-function-calling/03.3-how-function-calling-works.md)
- [2.3 A 50-line agent from scratch](../02-the-agent-loop/02.3-a-50-line-agent-from-scratch.md), for page 4.5
- [0.3 Setup](../00-start-here/00.3-setup.md), so you can run the code snippets
- Basic `async`/`await` in Python helps; the code snippets explain what they use

## 👀 Chapter overview

![Left: three AI apps each wired to four systems with twelve custom connectors. Right: each app has one MCP client and each system one MCP server, meeting at a shared MCP layer, so seven pieces are enough.](../../assets/diagrams/04-n-times-m-integrations.svg)

*The whole chapter in one picture. Pages 4.1 to 4.3 explain the right-hand side, 4.4 builds one of the servers, 4.5 builds one of the clients, and 4.6 asks what happens when a box on the right can't be trusted.*

## 📄 Pages in this chapter

<!-- PAGES:START -->
| # | Page | Level | Time |
| --- | --- | --- | --- |
| 4.1 | [Why MCP exists](./04.1-why-mcp-exists.md) — The integration problem MCP solves. | 🟢 Beginner | ~7 min |
| 4.2 | [Hosts, clients and servers](./04.2-hosts-clients-and-servers.md) — The three roles in MCP and how they talk. | 🟢 Beginner | ~8 min |
| 4.3 | [Tools, resources and prompts](./04.3-tools-resources-and-prompts.md) — The three things an MCP server can offer. | 🟡 Intermediate | ~10 min |
| 4.4 | [Build a simple MCP server](./04.4-build-a-simple-mcp-server.md) — Write and test your first MCP server in Python. | 🟡 Intermediate | ~15 min |
| 4.5 | [Connect MCP to an agent](./04.5-connect-mcp-to-an-agent.md) — Use an MCP server's tools from your own agent loop. | 🟡 Intermediate | ~12 min |
| 4.6 | [Security for MCP servers](./04.6-mcp-security.md) — Trust, permissions and the risks of third-party servers. | 🔴 Advanced | ~12 min |
<!-- PAGES:END -->

<!-- FOOTER -->

---

⬅️ **Previous chapter:** [03 · Tools & Function Calling](../03-tools-and-function-calling/README.md) ·
▶️ **Start reading:** [4.1 Why MCP exists](./04.1-why-mcp-exists.md) ·
➡️ **Next chapter:** [05 · Memory](../05-memory/README.md)
