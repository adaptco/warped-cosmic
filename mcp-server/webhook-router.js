// ============================================================
// AxQxOS Avatar Engine — Webhook Router
// mcp-server/webhook-router.js  |  v1.0.0
// Dispatches payloads in JSON, Markdown, and YAML formats
// ============================================================
import yaml from "js-yaml";
import { marked } from "marked";

export class WebhookRouter {

  async dispatch(url, receipt, format = "json") {
    const { body, contentType } = this.serialize(receipt, format);

    const res = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": contentType,
        "X-AxQxOS-Task-Id":  receipt.taskId,
        "X-AxQxOS-Schema":   receipt.schema,
        "X-AxQxOS-Version":  "v1.0.0",
        "X-AxQxOS-Canonical": "attested-replayable",
      },
      body,
    });

    return {
      url,
      status:    res.status,
      ok:        res.ok,
      format,
      timestamp: new Date().toISOString(),
    };
  }

  serialize(receipt, format) {
    switch (format) {
      case "yaml":
        return {
          body:        yaml.dump(receipt),
          contentType: "application/yaml",
        };
      case "markdown":
        return {
          body:        this.toMarkdown(receipt),
          contentType: "text/markdown",
        };
      default: // json
        return {
          body:        JSON.stringify(receipt, null, 2),
          contentType: "application/json",
        };
    }
  }

  toMarkdown(receipt) {
    return `# AxQxOS Task Receipt

| Field | Value |
|-------|-------|
| Task ID | \`${receipt.taskId}\` |
| Status | \`${receipt.status}\` |
| Role | \`${receipt.targetRole}\` |
| Format | \`${receipt.format}\` |
| Created | ${receipt.createdAt} |
| Completed | ${receipt.completedAt || "—"} |

## Payload
\`\`\`json
${JSON.stringify(receipt.payload, null, 2)}
\`\`\`

## Result
\`\`\`
${typeof receipt.result === "string" ? receipt.result : JSON.stringify(receipt.result, null, 2)}
\`\`\`

---
*Canonical truth, attested and replayable.*
`;
  }
}
