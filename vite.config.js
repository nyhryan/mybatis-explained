import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import { Marked, Renderer } from "marked";
import markedCjkFriendly from "marked-cjk-friendly";
import { createHighlighter } from "shiki";
import { defineConfig } from "vite";
import { viteSingleFile } from "vite-plugin-singlefile";

const manuscript = fileURLToPath(new URL("./docs/mybatis-guide.md", import.meta.url));
const highlighter = await createHighlighter({
  themes: ["github-light"],
  langs: ["java", "xml", "sql"],
});

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function manuscriptPlugin() {
  return {
    name: "mybatis-manuscript",
    configureServer(server) {
      server.watcher.add(manuscript);
      server.watcher.on("change", (path) => {
        if (path === manuscript) server.ws.send({ type: "full-reload" });
      });
    },
    async transformIndexHtml(html) {
      const source = await readFile(manuscript, "utf8");
      const headings = [];
      const marked = new Marked(markedCjkFriendly());
      marked.use({
        renderer: {
          heading({ tokens, depth }) {
            const content = this.parser.parseInline(tokens);
            const id = `section-${headings.length + 1}`;
            headings.push({ id, depth, content });
            return `<h${depth} id="${id}">${content}</h${depth}>\n`;
          },
          code({ text, lang }) {
            const language = (lang || "text").split(/\s/)[0];
            const label =
              { java: "Java", xml: "XML", sql: "SQL", text: "텍스트" }[language] || "텍스트";
            const highlighted = ["java", "xml", "sql"].includes(language)
              ? highlighter.codeToHtml(text, {
                  lang: language,
                  theme: "github-light",
                  tabindex: false,
                })
              : `<pre><code>${escapeHtml(text)}</code></pre>\n`;
            const pre = highlighted.replace(
              "<pre",
              `<pre tabindex="0" role="region" aria-label="${label} 코드, 가로 스크롤 가능"`,
            );
            return `<div class="code-block">${pre}</div>\n`;
          },
          table(token) {
            const renderer = new Renderer();
            renderer.parser = this.parser;
            return `<div class="table-scroll" tabindex="0" role="region" aria-label="표, 가로 스크롤 가능">${renderer.table(token)}</div>\n`;
          },
        },
      });
      const content = await marked.parse(source);
      const toc = headings
        .filter(({ depth }) => depth > 1)
        .map(
          ({ id, depth, content }) =>
            `<li class="toc-depth-${depth}"><a href="#${id}">${content}</a></li>`,
        )
        .join("\n");
      return html
        .replace("<!-- TABLE_OF_CONTENTS -->", toc)
        .replace("<!-- MANUSCRIPT -->", content);
    },
  };
}

export default defineConfig({
  plugins: [tailwindcss(), manuscriptPlugin(), viteSingleFile()],
});
