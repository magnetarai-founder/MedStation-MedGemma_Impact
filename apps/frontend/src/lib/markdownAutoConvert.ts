/**
 * Markdown Auto-Conversion Utility
 *
 * Automatically converts markdown syntax to formatted text as you type
 * Inspired by Notion's inline markdown formatting
 */

export interface MarkdownConversion {
  type: 'bold' | 'italic' | 'code' | 'strikethrough' | 'link' | 'none'
  matchStart: number
  matchEnd: number
  replacement: string
  rawText: string
}

/**
 * Detect markdown patterns in text and return conversion details
 */
export function detectMarkdown(text: string, cursorPos: number): MarkdownConversion | null {
  const beforeCursor = text.slice(0, cursorPos)

  // **bold** → <strong>bold</strong>
  const boldMatch = beforeCursor.match(/\*\*(.+?)\*\*$/)
  if (boldMatch && boldMatch[1]) {
    return {
      type: 'bold',
      matchStart: cursorPos - boldMatch[0].length,
      matchEnd: cursorPos,
      replacement: `<strong>${boldMatch[1]}</strong>`,
      rawText: boldMatch[1],
    }
  }

  // __bold__ → <strong>bold</strong> (alternative syntax)
  const boldUnderscoreMatch = beforeCursor.match(/__(.+?)__$/)
  if (boldUnderscoreMatch && boldUnderscoreMatch[1]) {
    return {
      type: 'bold',
      matchStart: cursorPos - boldUnderscoreMatch[0].length,
      matchEnd: cursorPos,
      replacement: `<strong>${boldUnderscoreMatch[1]}</strong>`,
      rawText: boldUnderscoreMatch[1],
    }
  }

  // *italic* → <em>italic</em>
  const italicMatch = beforeCursor.match(/\*([^*]+)\*$/)
  if (italicMatch && italicMatch[1]) {
    return {
      type: 'italic',
      matchStart: cursorPos - italicMatch[0].length,
      matchEnd: cursorPos,
      replacement: `<em>${italicMatch[1]}</em>`,
      rawText: italicMatch[1],
    }
  }

  // _italic_ → <em>italic</em> (alternative syntax)
  const italicUnderscoreMatch = beforeCursor.match(/_([^_]+)_$/)
  if (italicUnderscoreMatch && italicUnderscoreMatch[1]) {
    return {
      type: 'italic',
      matchStart: cursorPos - italicUnderscoreMatch[0].length,
      matchEnd: cursorPos,
      replacement: `<em>${italicUnderscoreMatch[1]}</em>`,
      rawText: italicUnderscoreMatch[1],
    }
  }

  // `code` → <code>code</code>
  const codeMatch = beforeCursor.match(/`([^`]+)`$/)
  if (codeMatch && codeMatch[1]) {
    return {
      type: 'code',
      matchStart: cursorPos - codeMatch[0].length,
      matchEnd: cursorPos,
      replacement: `<code>${escapeHtml(codeMatch[1])}</code>`,
      rawText: codeMatch[1],
    }
  }

  // ~~strikethrough~~ → <del>strikethrough</del>
  const strikethroughMatch = beforeCursor.match(/~~(.+?)~~$/)
  if (strikethroughMatch && strikethroughMatch[1]) {
    return {
      type: 'strikethrough',
      matchStart: cursorPos - strikethroughMatch[0].length,
      matchEnd: cursorPos,
      replacement: `<del>${strikethroughMatch[1]}</del>`,
      rawText: strikethroughMatch[1],
    }
  }

  // [link text](url) → <a href="url">link text</a>
  const linkMatch = beforeCursor.match(/\[([^\]]+)\]\(([^)]+)\)$/)
  if (linkMatch && linkMatch[1] && linkMatch[2]) {
    return {
      type: 'link',
      matchStart: cursorPos - linkMatch[0].length,
      matchEnd: cursorPos,
      replacement: `<a href="${escapeHtml(linkMatch[2])}" target="_blank" rel="noopener noreferrer">${linkMatch[1]}</a>`,
      rawText: linkMatch[1],
    }
  }

  return null
}

/**
 * Check if a space or enter key should trigger markdown conversion
 */
export function shouldTriggerConversion(
  text: string,
  cursorPos: number,
  key: string
): boolean {
  // Trigger on space or enter
  if (key !== ' ' && key !== 'Enter') {
    return false
  }

  // Check if there's a valid markdown pattern before cursor
  const conversion = detectMarkdown(text, cursorPos)
  return conversion !== null
}

/**
 * Apply markdown conversion to text
 */
export function applyMarkdownConversion(
  text: string,
  conversion: MarkdownConversion
): { newText: string; newCursorPos: number } {
  const before = text.slice(0, conversion.matchStart)
  const after = text.slice(conversion.matchEnd)
  const newText = before + conversion.replacement + after

  // Calculate new cursor position (after the replaced text)
  const newCursorPos = before.length + conversion.replacement.length

  return { newText, newCursorPos }
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text: string): string {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

/**
 * Convert markdown block syntax at start of line
 */
export function detectBlockMarkdown(
  line: string
): { type: string; content: string } | null {
  // # Heading 1
  if (/^#\s+(.+)$/.test(line)) {
    const match = line.match(/^#\s+(.+)$/)
    return { type: 'h1', content: match![1] }
  }

  // ## Heading 2
  if (/^##\s+(.+)$/.test(line)) {
    const match = line.match(/^##\s+(.+)$/)
    return { type: 'h2', content: match![1] }
  }

  // ### Heading 3
  if (/^###\s+(.+)$/.test(line)) {
    const match = line.match(/^###\s+(.+)$/)
    return { type: 'h3', content: match![1] }
  }

  // - Bullet list
  if (/^[-*]\s+(.+)$/.test(line)) {
    const match = line.match(/^[-*]\s+(.+)$/)
    return { type: 'bullet', content: match![1] }
  }

  // 1. Numbered list
  if (/^\d+\.\s+(.+)$/.test(line)) {
    const match = line.match(/^\d+\.\s+(.+)$/)
    return { type: 'numbered', content: match![1] }
  }

  // - [ ] Todo item
  if (/^[-*]\s+\[\s*\]\s+(.+)$/.test(line)) {
    const match = line.match(/^[-*]\s+\[\s*\]\s+(.+)$/)
    return { type: 'todo', content: match![1] }
  }

  // - [x] Completed todo
  if (/^[-*]\s+\[x\]\s+(.+)$/i.test(line)) {
    const match = line.match(/^[-*]\s+\[x\]\s+(.+)$/i)
    return { type: 'todo-completed', content: match![1] }
  }

  // > Quote
  if (/^>\s+(.+)$/.test(line)) {
    const match = line.match(/^>\s+(.+)$/)
    return { type: 'quote', content: match![1] }
  }

  // ``` Code block
  if (/^```/.test(line)) {
    return { type: 'code-block', content: '' }
  }

  // --- Horizontal rule
  if (/^---+$/.test(line) || /^___+$/.test(line) || /^\*\*\*+$/.test(line)) {
    return { type: 'hr', content: '' }
  }

  return null
}

/**
 * Check if text contains any markdown syntax
 */
export function hasMarkdownSyntax(text: string): boolean {
  const patterns = [
    /\*\*[^*]+\*\*/,  // **bold**
    /__[^_]+__/,      // __bold__
    /\*[^*]+\*/,      // *italic*
    /_[^_]+_/,        // _italic_
    /`[^`]+`/,        // `code`
    /~~[^~]+~~/,      // ~~strikethrough~~
    /\[.+\]\(.+\)/,   // [link](url)
    /^#{1,6}\s/m,     // # headings
    /^[-*]\s/m,       // - list
    /^\d+\.\s/m,      // 1. list
    /^>\s/m,          // > quote
  ]

  return patterns.some(pattern => pattern.test(text))
}

/**
 * Strip markdown syntax from text (get plain text)
 */
export function stripMarkdown(text: string): string {
  return text
    // Remove bold
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/__([^_]+)__/g, '$1')
    // Remove italic
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/_([^_]+)_/g, '$1')
    // Remove code
    .replace(/`([^`]+)`/g, '$1')
    // Remove strikethrough
    .replace(/~~([^~]+)~~/g, '$1')
    // Remove links
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    // Remove headings
    .replace(/^#{1,6}\s+/gm, '')
    // Remove list markers
    .replace(/^[-*]\s+/gm, '')
    .replace(/^\d+\.\s+/gm, '')
    // Remove quotes
    .replace(/^>\s+/gm, '')
    // Remove code blocks
    .replace(/```[\s\S]*?```/g, '')
}

/**
 * Convert markdown to HTML (simple conversion)
 */
export function markdownToHtml(markdown: string): string {
  let html = markdown

  // Block elements (must come first)
  html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  html = html.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
  html = html.replace(/^[-*] (.+)$/gm, '<li>$1</li>')

  // Inline elements
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  html = html.replace(/_([^_]+)_/g, '<em>$1</em>')
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  html = html.replace(/~~([^~]+)~~/g, '<del>$1</del>')
  html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')

  return html
}
