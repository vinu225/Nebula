"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download, Copy, Check, Code2, ExternalLink, FileText, CheckCircle2, Eye, FolderPlus } from "lucide-react";
import { API_BASE } from "@/lib/api";
import { LivePreviewModal } from "@/components/LivePreviewModal";
import { SaveProjectModal } from "@/components/SaveProjectModal";

interface ChatMessageContentProps {
  content: string;
}

export const ChatMessageContent: React.FC<ChatMessageContentProps> = ({ content }) => {
  return (
    <div className="markdown-body text-xs leading-relaxed text-slate-200 space-y-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-base font-bold text-white border-b border-slate-800 pb-1.5 mt-4 mb-2">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm font-bold text-emerald-400 border-b border-slate-800/60 pb-1 mt-3.5 mb-2">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs font-bold text-emerald-300 uppercase tracking-wider mt-3 mb-1.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block"></span>
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-xs font-semibold text-slate-100 mt-2.5 mb-1 text-emerald-400/90">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="my-1.5 leading-relaxed text-slate-300 font-normal">
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong className="font-semibold text-white tracking-wide">
              {children}
            </strong>
          ),
          em: ({ children }) => (
            <em className="text-slate-300 italic">{children}</em>
          ),
          ul: ({ children }) => (
            <ul className="space-y-1 my-2 ml-1 text-slate-300">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="list-decimal list-outside space-y-1 my-2 ml-4 text-slate-300">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="flex items-start gap-2 leading-relaxed">
              <span className="text-emerald-400 font-bold select-none leading-5">•</span>
              <div className="flex-1 min-w-0">{children}</div>
            </li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="border-l-2 border-emerald-500/60 bg-slate-900/60 pl-3 py-1.5 my-2 rounded-r text-slate-300 italic text-[11px]">
              {children}
            </blockquote>
          ),
          hr: () => (
            <hr className="my-3 border-slate-800/80" />
          ),
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/60">
              <table className="w-full text-left border-collapse text-[11px]">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-slate-900 border-b border-slate-800 text-slate-300 font-semibold uppercase text-[10px] tracking-wider">
              {children}
            </thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-slate-900/40 transition-colors">
              {children}
            </tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-slate-200">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2">{children}</td>
          ),
          a: ({ href, children }) => {
            const rawUrl = href || "#";
            // Check if it's an artifact download
            const isArtifactDownload =
              rawUrl.includes("/download") ||
              rawUrl.includes("/artifacts/") ||
              /\.(docx|xlsx|pdf|py|cpp|c|sh|sql)$/i.test(rawUrl);

            let targetUrl = rawUrl;
            if (targetUrl.startsWith("/api/")) {
              targetUrl = `${API_BASE}${targetUrl}`;
            }

            if (isArtifactDownload) {
              return (
                <a
                  href={targetUrl}
                  download
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 my-1 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 hover:text-emerald-100 border border-emerald-500/40 text-[11px] font-semibold transition-all shadow-sm hover:shadow-emerald-950/50 cursor-pointer group"
                >
                  <Download className="w-3.5 h-3.5 text-emerald-400 group-hover:scale-110 group-hover:-translate-y-0.5 transition-transform" />
                  <span className="underline underline-offset-2">{children}</span>
                </a>
              );
            }

            return (
              <a
                href={targetUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-emerald-400 hover:text-emerald-300 underline underline-offset-2 font-medium"
              >
                <span>{children}</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            );
          },
          code: ({ className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || "");
            const codeString = String(children).replace(/\n$/, "");
            const isInline = !match && !codeString.includes("\n");

            if (isInline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-slate-800 text-emerald-300 font-mono text-[11px] border border-slate-700/60"
                  {...props}
                >
                  {children}
                </code>
              );
            }

            const lang = match ? match[1] : "";
            return <CodeBlockWithCopy lang={lang} code={codeString} fullMarkdown={content} />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};

function parseWebCodeBlocks(markdown: string) {
  const codeBlockRegex = /```(\w+)?\s*\n([\s\S]*?)\n```/g;
  let match;
  let htmlCode = "";
  let cssCode = "";
  let jsCode = "";

  while ((match = codeBlockRegex.exec(markdown)) !== null) {
    const l = (match[1] || "").toLowerCase();
    const c = match[2].trim();

    if (l === "html" || c.includes("<!DOCTYPE") || c.includes("<html") || c.includes("<body")) {
      if (!htmlCode) htmlCode = c;
    } else if (l === "css" || (!cssCode && c.includes("{") && (c.includes("margin:") || c.includes("color:") || c.includes("background")))) {
      cssCode += (cssCode ? "\n\n" : "") + c;
    } else if (["js", "javascript"].includes(l) || (!jsCode && (c.includes("document.") || c.includes("addEventListener") || c.includes("console.log")))) {
      jsCode += (jsCode ? "\n\n" : "") + c;
    }
  }

  return { htmlCode, cssCode, jsCode };
}

function getBundledPreviewAndFiles(currentCode: string, currentLang: string, markdown: string) {
  const { htmlCode, cssCode, jsCode } = parseWebCodeBlocks(markdown);

  // If current block or markdown has HTML
  let html = (currentCode.includes("<html") || currentCode.includes("<!DOCTYPE") || currentCode.includes("<body") || currentCode.includes("<div") || currentCode.includes("<header"))
    ? currentCode
    : (htmlCode || currentCode);

  const css = cssCode || (currentLang === "css" ? currentCode : "");
  const js = jsCode || (["js", "javascript"].includes(currentLang) ? currentCode : "");

  // Inject CSS if not already present
  if (css && !html.includes(css.substring(0, Math.min(25, css.length)))) {
    if (html.includes("</head>")) {
      html = html.replace("</head>", `<style>\n${css}\n</style>\n</head>`);
    } else if (html.includes("<body")) {
      html = `<style>\n${css}\n</style>\n` + html;
    } else {
      html = `<style>\n${css}\n</style>\n` + html;
    }
  }

  // Inject JS if not already present
  if (js && !html.includes(js.substring(0, Math.min(25, js.length)))) {
    if (html.includes("</body>")) {
      html = html.replace("</body>", `<script>\n${js}\n</script>\n</body>`);
    } else {
      html = html + `\n<script>\n${js}\n</script>`;
    }
  }

  // Multi-file collection for Save to Disk (Mini Antigravity)
  const files: Array<{ filename: string; content: string }> = [];
  if (htmlCode) {
    files.push({ filename: "index.html", content: htmlCode });
  } else if (currentCode.includes("<")) {
    files.push({ filename: "index.html", content: currentCode });
  }
  if (css) {
    files.push({ filename: "styles.css", content: css });
  }
  if (js) {
    files.push({ filename: "script.js", content: js });
  }
  if (files.length === 0) {
    files.push({ filename: "solution.txt", content: currentCode });
  }

  return { bundledHtml: html, files };
}

const CodeBlockWithCopy: React.FC<{ lang: string; code: string; fullMarkdown?: string }> = ({
  lang,
  code,
  fullMarkdown = "",
}) => {
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(false);
  const [showSaveModal, setShowSaveModal] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isWebCode =
    ["html", "htm", "svg", "xml", "jsx", "tsx"].includes(lang.toLowerCase()) ||
    code.includes("<!DOCTYPE") ||
    code.includes("<html") ||
    code.includes("<body") ||
    code.includes("<div") ||
    code.includes("<header") ||
    code.includes("<button") ||
    code.includes("<script");

  const { bundledHtml, files } = getBundledPreviewAndFiles(code, lang, fullMarkdown);

  return (
    <>
      <div className="my-3 rounded-xl overflow-hidden border border-slate-800 bg-slate-950 shadow-lg font-mono text-[11px]">
        <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900/90 border-b border-slate-800 text-slate-400">
          <span className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-semibold uppercase tracking-wider">
            <Code2 className="w-3.5 h-3.5" />
            {lang || "code"}
          </span>

          <div className="flex items-center space-x-1.5">
            {/* Live Preview Button */}
            {isWebCode && (
              <button
                onClick={() => setShowPreview(true)}
                className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-semibold text-emerald-300 bg-emerald-950/60 hover:bg-emerald-900/80 border border-emerald-500/40 hover:border-emerald-400 transition cursor-pointer shadow-sm shadow-emerald-950/40 group"
                title="Preview live rendered web interface"
              >
                <Eye className="w-3 h-3 text-emerald-400 group-hover:scale-110 transition-transform" />
                <span>Live Preview</span>
              </button>
            )}

            {/* Save to Filesystem (Mini Antigravity) Button */}
            <button
              onClick={() => setShowSaveModal(true)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium text-blue-300 bg-blue-950/50 hover:bg-blue-900/70 border border-blue-500/30 hover:border-blue-400 transition cursor-pointer"
              title="Create folder and write file to workspace disk"
            >
              <FolderPlus className="w-3 h-3 text-blue-400" />
              <span>Save to Disk</span>
            </button>

            {/* Copy Button */}
            <button
              onClick={handleCopy}
              className="flex items-center gap-1 px-2.5 py-1 rounded-md text-[10px] font-medium text-slate-400 hover:text-white hover:bg-slate-800 border border-transparent hover:border-slate-700 transition cursor-pointer"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-400" />
                  <span className="text-emerald-400">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span>Copy</span>
                </>
              )}
            </button>
          </div>
        </div>

        <pre className="p-3.5 overflow-x-auto text-slate-200 leading-relaxed scrollbar-thin scrollbar-thumb-slate-800">
          <code>{code}</code>
        </pre>
      </div>

      {/* Modals */}
      <LivePreviewModal
        isOpen={showPreview}
        onClose={() => setShowPreview(false)}
        code={bundledHtml}
        title="Live Interactive Preview"
        onOpenSaveModal={() => {
          setShowPreview(false);
          setShowSaveModal(true);
        }}
      />

      <SaveProjectModal
        isOpen={showSaveModal}
        onClose={() => setShowSaveModal(false)}
        files={files}
      />
    </>
  );
};
