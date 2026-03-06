import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import crypto from "node:crypto";

import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { z } from "zod";

type BackendToolResult = {
  tool_name: string;
  ok: boolean;
  result: Record<string, unknown>;
  request_id: string;
  trace_id?: string;
};

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, "..");
const WIDGET_URI = "ui://widget/embedding-workspace-v1.html";
const WIDGET_HTML = readFileSync(path.join(ROOT_DIR, "public", "widget.html"), "utf8");

const APP_NAME = "a2a-mcp-embedding-studio";
const APP_VERSION = "1.0.0";
const PORT = Number(process.env.PORT ?? "8787");
const MCP_PATH = "/mcp";

const CHATGPT_APP_DOMAIN = process.env.CHATGPT_APP_DOMAIN?.trim() ?? "";
const CHATGPT_APP_BACKEND_URL =
  process.env.CHATGPT_APP_BACKEND_URL?.trim() ?? "http://127.0.0.1:8080/tools/call";
const CHATGPT_APP_PRIVACY_URL =
  process.env.CHATGPT_APP_PRIVACY_URL?.trim() ?? "https://example.com/privacy";
const CHATGPT_APP_SUPPORT_URL =
  process.env.CHATGPT_APP_SUPPORT_URL?.trim() ?? "https://example.com/support";
const BACKEND_BEARER = process.env.CHATGPT_APP_BACKEND_BEARER?.trim() ?? "";
const REQUEST_TIMEOUT_MS = Number(process.env.CHATGPT_APP_TIMEOUT_MS ?? "30000");

const GITHUB_AUTH_URL =
  process.env.GITHUB_OAUTH_AUTHORIZE_URL?.trim() ?? "https://github.com/login/oauth/authorize";
const GITHUB_TOKEN_URL =
  process.env.GITHUB_OAUTH_TOKEN_URL?.trim() ?? "https://github.com/login/oauth/access_token";

const READ_SCOPES = parseScopes(
  process.env.GITHUB_OAUTH_REQUIRED_SCOPES_READ ?? "read:user"
);
const WRITE_SCOPES = parseScopes(
  process.env.GITHUB_OAUTH_REQUIRED_SCOPES_WRITE ?? "repo"
);

const RESOURCE_DOMAINS = compact([
  CHATGPT_APP_DOMAIN,
  process.env.CHATGPT_APP_RESOURCE_DOMAIN?.trim() ?? "",
]).map((value) => normalizeDomain(value));

const CONNECT_DOMAINS = compact([
  toDomain(CHATGPT_APP_BACKEND_URL),
  "https://api.github.com",
]).map((value) => normalizeDomain(value));

function createAppServer(): McpServer {
  const server = new McpServer({
    name: APP_NAME,
    version: APP_VERSION,
  });

  registerAppResource(server, "embedding-widget", WIDGET_URI, {}, async () => ({
    contents: [
      {
        uri: WIDGET_URI,
        mimeType: RESOURCE_MIME_TYPE,
        text: WIDGET_HTML,
        _meta: {
          ui: {
            prefersBorder: true,
            domain: CHATGPT_APP_DOMAIN || undefined,
            csp: {
              connectDomains: CONNECT_DOMAINS,
              resourceDomains: RESOURCE_DOMAINS,
            },
          },
          "openai/widgetDescription":
            "Interactive A2A_MCP embedding studio for search, upsert, and orchestration command execution.",
        },
      },
    ],
  }));

  (registerAppTool as any)(
    server,
    "embedding_search",
    buildToolConfig({
      title: "Embedding Search",
      description:
        "Use this when the user needs semantic retrieval over MCP embedding records.",
      readOnly: true,
      idempotent: true,
      scopes: READ_SCOPES,
      invocationLabel: "Searching embedding records",
      completeLabel: "Embedding search complete",
      inputSchema: {
        query: z.string().min(1).describe("Semantic query string."),
        top_k: z.number().int().min(1).max(25).default(5),
        namespace: z.string().optional(),
      },
    }),
    async (input: Record<string, unknown>, context: unknown) => {
      const backend = await callBackendTool({
        toolName: "embedding_search",
        arguments: {
          query: input.query,
          top_k: input.top_k ?? 5,
          namespace: input.namespace,
        },
        context,
      });
      return buildToolResponse({
        text: `Embedding search returned ${asArray(backend.result.matches).length} matches.`,
        backend,
      });
    }
  );

  (registerAppTool as any)(
    server,
    "embedding_upsert",
    buildToolConfig({
      title: "Embedding Upsert",
      description:
        "Use this when the user wants to add or update an embedding record in a namespace.",
      readOnly: false,
      idempotent: true,
      scopes: WRITE_SCOPES,
      invocationLabel: "Writing embedding record",
      completeLabel: "Embedding upsert complete",
      inputSchema: {
        namespace: z.string().min(1),
        text: z.string().min(1),
        metadata: z.record(z.unknown()).optional(),
      },
    }),
    async (input: Record<string, unknown>, context: unknown) => {
      const backend = await callBackendTool({
        toolName: "embedding_upsert",
        arguments: {
          namespace: input.namespace,
          text: input.text,
          metadata: input.metadata ?? {},
        },
        context,
      });
      const status = String(backend.result.status ?? "updated");
      return buildToolResponse({
        text: `Embedding ${status}: ${String(backend.result.record_id ?? "unknown")}.`,
        backend,
      });
    }
  );

  (registerAppTool as any)(
    server,
    "orchestrate_command",
    buildToolConfig({
      title: "Orchestrate Command",
      description:
        "Use this when the user needs to run orchestrator commands like !run, !triage, or !deploy.",
      readOnly: false,
      idempotent: false,
      scopes: WRITE_SCOPES,
      invocationLabel: "Running orchestrator command",
      completeLabel: "Orchestrator command completed",
      inputSchema: {
        command: z.string().min(1),
        args: z.string().optional(),
        slack: z
          .object({
            channel_id: z.string().min(1),
            thread_ts: z.string().optional(),
          })
          .optional(),
      },
    }),
    async (input: Record<string, unknown>, context: unknown) => {
      const backend = await callBackendTool({
        toolName: "orchestrate_command",
        arguments: {
          command: input.command,
          args: input.args,
          slack: input.slack,
        },
        context,
      });
      return buildToolResponse({
        text: `Orchestration status: ${String(backend.result.status ?? "unknown")}.`,
        backend,
      });
    }
  );

  (registerAppTool as any)(
    server,
    "embedding_workspace_data",
    buildToolConfig({
      title: "Embedding Workspace Data",
      description:
        "Use this when the user wants vectors, projections, and namespace summaries for the embedding studio.",
      readOnly: true,
      idempotent: true,
      scopes: READ_SCOPES,
      invocationLabel: "Loading workspace vectors",
      completeLabel: "Workspace vectors loaded",
      inputSchema: {
        namespace: z.string().optional(),
        query: z.string().optional(),
        top_k: z.number().int().min(1).max(25).default(5),
      },
    }),
    async (input: Record<string, unknown>, context: unknown) => {
      const backend = await callBackendTool({
        toolName: "embedding_workspace_data",
        arguments: {
          namespace: input.namespace,
          query: input.query,
          top_k: input.top_k ?? 5,
        },
        context,
      });
      return buildToolResponse({
        text: "Workspace data loaded for embedding visualization.",
        backend,
      });
    }
  );

  (registerAppTool as any)(
    server,
    "render_embedding_workspace",
    buildToolConfig({
      title: "Render Embedding Workspace",
      description:
        "Use this after data operations to render the embedding widget with the latest workspace context.",
      readOnly: true,
      idempotent: true,
      scopes: READ_SCOPES,
      invocationLabel: "Rendering embedding workspace",
      completeLabel: "Embedding workspace ready",
      inputSchema: {
        namespace: z.string().optional(),
        query: z.string().optional(),
      },
    }),
    async (input: Record<string, unknown>, context: unknown) => {
      const backend = await callBackendTool({
        toolName: "embedding_workspace_data",
        arguments: {
          namespace: input.namespace,
          query: input.query,
          top_k: 8,
        },
        context,
      });
      return buildToolResponse({
        text: "Rendered embedding workspace widget.",
        backend,
      });
    }
  );

  return server;
}

createServer(async (req, res) => {
  if (!req.url) {
    res.writeHead(400).end("Missing URL");
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host ?? "localhost"}`);
  const isMcpRoute = url.pathname === MCP_PATH || url.pathname.startsWith(`${MCP_PATH}/`);

  if (req.method === "OPTIONS" && isMcpRoute) {
    res.writeHead(204, {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, GET, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "content-type, mcp-session-id",
      "Access-Control-Expose-Headers": "Mcp-Session-Id",
    });
    res.end();
    return;
  }

  if (req.method === "GET" && url.pathname === "/") {
    res.writeHead(200, { "content-type": "application/json" }).end(
      JSON.stringify(
        {
          name: APP_NAME,
          version: APP_VERSION,
          mcp_path: MCP_PATH,
          backend: CHATGPT_APP_BACKEND_URL,
          privacy_url: CHATGPT_APP_PRIVACY_URL,
          support_url: CHATGPT_APP_SUPPORT_URL,
        },
        null,
        2
      )
    );
    return;
  }

  if (isMcpRoute && req.method && new Set(["GET", "POST", "DELETE"]).has(req.method)) {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Expose-Headers", "Mcp-Session-Id");

    const server = createAppServer();
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true,
    });

    res.on("close", () => {
      transport.close();
      server.close();
    });

    try {
      await server.connect(transport);
      await transport.handleRequest(req, res);
    } catch (error) {
      console.error("Failed to handle MCP request:", error);
      if (!res.headersSent) {
        res.writeHead(500).end("Internal server error");
      }
    }
    return;
  }

  res.writeHead(404).end("Not Found");
}).listen(PORT, () => {
  console.log(`${APP_NAME} listening on http://localhost:${PORT}${MCP_PATH}`);
});

function buildToolConfig(input: {
  title: string;
  description: string;
  readOnly: boolean;
  idempotent: boolean;
  scopes: string[];
  invocationLabel: string;
  completeLabel: string;
  inputSchema: any;
}) {
  const securityScheme = githubSecurityScheme(input.scopes);
  return {
    title: input.title,
    description: input.description,
    inputSchema: input.inputSchema,
    annotations: {
      readOnlyHint: input.readOnly,
      destructiveHint: !input.readOnly,
      openWorldHint: false,
      idempotentHint: input.idempotent,
    },
    securitySchemes: [securityScheme],
    _meta: {
      ui: { resourceUri: WIDGET_URI },
      securitySchemes: [securityScheme],
      "openai/toolInvocation/invoking": input.invocationLabel,
      "openai/toolInvocation/invoked": input.completeLabel,
    },
  } as any;
}

function buildToolResponse(input: {
  text: string;
  backend: BackendToolResult;
}) {
  const backendResult = input.backend.result ?? {};
  return {
    content: [{ type: "text" as const, text: input.text }],
    structuredContent: {
      tool_name: input.backend.tool_name,
      backend_ok: input.backend.ok,
      ...backendResult,
      request_id: input.backend.request_id,
      trace_id: input.backend.trace_id ?? input.backend.request_id,
    },
    _meta: {
      "openai/outputTemplate": WIDGET_URI,
      backend_request_id: input.backend.request_id,
      backend_trace_id: input.backend.trace_id ?? input.backend.request_id,
      privacy_url: CHATGPT_APP_PRIVACY_URL,
      support_url: CHATGPT_APP_SUPPORT_URL,
    },
  };
}

function githubSecurityScheme(scopes: string[]) {
  return {
    type: "oauth2",
    authorizationUrl: GITHUB_AUTH_URL,
    tokenUrl: GITHUB_TOKEN_URL,
    scopes,
  };
}

async function callBackendTool(input: {
  toolName: string;
  arguments: Record<string, unknown>;
  context: unknown;
}): Promise<BackendToolResult> {
  const requestId = crypto.randomUUID();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "X-Request-ID": requestId,
  };

  const bearer = resolveBearer(input.context);
  if (bearer) {
    headers.Authorization = bearer.startsWith("Bearer ") ? bearer : `Bearer ${bearer}`;
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(CHATGPT_APP_BACKEND_URL, {
      method: "POST",
      headers,
      body: JSON.stringify({
        tool_name: input.toolName,
        arguments: input.arguments,
      }),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timeout);
  }

  let body: unknown = {};
  try {
    body = await response.json();
  } catch {
    body = {};
  }

  if (!response.ok) {
    throw new Error(
      `Backend tool call failed (${response.status}): ${JSON.stringify(body)}`
    );
  }

  const parsed = body as Record<string, unknown>;
  const backendResult = (parsed.result as Record<string, unknown> | undefined) ?? {};
  return {
    tool_name: String(parsed.tool_name ?? input.toolName),
    ok: Boolean(parsed.ok),
    result: backendResult,
    request_id: String(parsed.request_id ?? requestId),
    trace_id: String(parsed.trace_id ?? backendResult.trace_id ?? requestId),
  };
}

function resolveBearer(context: unknown): string {
  if (BACKEND_BEARER) {
    return BACKEND_BEARER;
  }
  const ctx = (context ?? {}) as Record<string, unknown>;
  const auth = ctx.auth as Record<string, unknown> | undefined;
  const meta = ctx._meta as Record<string, unknown> | undefined;

  const candidates = [
    ctx.authorization,
    auth?.accessToken,
    auth?.token,
    meta?.authorization,
    meta?.accessToken,
  ];
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  }
  return "";
}

function parseScopes(value: string): string[] {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

function compact(values: string[]): string[] {
  return values.map((value) => value.trim()).filter((value) => value.length > 0);
}

function normalizeDomain(domain: string): string {
  if (domain.startsWith("http://") || domain.startsWith("https://")) {
    return domain;
  }
  return `https://${domain}`;
}

function toDomain(value: string): string {
  try {
    const url = new URL(value);
    return `${url.protocol}//${url.host}`;
  } catch {
    return value;
  }
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}
