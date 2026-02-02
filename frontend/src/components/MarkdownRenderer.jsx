import React, { useMemo } from 'react';
import './markdown.css';

const MarkdownRenderer = ({ content, isStreaming = false }) => {
  const processedContent = useMemo(() => {
    if (!content) return '';
    
    if (isStreaming) {
      return processStreamingMarkdown(content);
    }
    
    return processCompleteMarkdown(content);
  }, [content, isStreaming]);

  return (
    <div 
      className="markdown-content"
      dangerouslySetInnerHTML={{ __html: processedContent }} 
    />
  );
};

function processStreamingMarkdown(content) {
  // For streaming, only process complete markdown blocks to avoid flickering
  const lines = content.split('\n');
  let processed = '';
  let inCodeBlock = false;
  let codeBlockContent = '';
  let codeBlockLang = '';
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    
    if (line.startsWith('```')) {
      if (!inCodeBlock) {
        // Starting code block
        inCodeBlock = true;
        codeBlockLang = line.slice(3).trim();
        codeBlockContent = '';
      } else {
        // Ending code block - render complete block
        inCodeBlock = false;
        processed += `<pre><code class="language-${codeBlockLang}">${escapeHtml(codeBlockContent)}</code></pre>\n`;
        codeBlockContent = '';
      }
    } else if (inCodeBlock) {
      codeBlockContent += line + '\n';
    } else {
      // Process other markdown elements for complete lines
      processed += processMarkdownLine(line) + '\n';
    }
  }
  
  // If still in code block, show partial content
  if (inCodeBlock && codeBlockContent) {
    processed += `<pre><code class="language-${codeBlockLang}">${escapeHtml(codeBlockContent)}</code></pre>`;
  }
  
  return processed;
}

function processCompleteMarkdown(content) {
  let processed = content;
  
  // Headers
  processed = processed.replace(/^### (.*$)/gm, '<h3>$1</h3>');
  processed = processed.replace(/^## (.*$)/gm, '<h2>$1</h2>');
  processed = processed.replace(/^# (.*$)/gm, '<h1>$1</h1>');
  
  // Horizontal rules
  processed = processed.replace(/^\s*(---|\*\*\*|___)\s*$/gm, '<hr />');
  
  // Bold and italic
  processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  processed = processed.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Code blocks
  processed = processed.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang || ''}">${escapeHtml(code.trim())}</code></pre>`;
  });
  
  // Inline code
  processed = processed.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Unordered lists
  processed = wrapListBlocks(processed, /\n?\*\s+.+/g, /^\*\s+(.+)$/gm, 'ul');
  
  // Ordered lists (e.g., 1. item)
  processed = wrapListBlocks(processed, /\n?\d+\.\s+.+/g, /^(\d+)\.\s+(.+)$/gm, 'ol');
  
  // Tables (GitHub-Flavored Markdown)
  processed = processed.replace(/((?:^\|.*\n)+)(?:^\s*$|^$)/gm, (block) => {
    const html = renderMarkdownTable(block.trim());
    return html || block; // fallback to original if not a valid table
  });
  
  // Line breaks
  processed = processed.replace(/\n\n/g, '</p><p>');
  processed = '<p>' + processed + '</p>';
  
  // Clean up empty paragraphs
  processed = processed.replace(/<p><\/p>/g, '');
  processed = processed.replace(/<p>(<h[1-6]>)/g, '$1');
  processed = processed.replace(/(<\/h[1-6]>)<\/p>/g, '$1');
  processed = processed.replace(/<p>(<pre>)/g, '$1');
  processed = processed.replace(/(<\/pre>)<\/p>/g, '$1');
  processed = processed.replace(/<p>(<ul>)/g, '$1');
  processed = processed.replace(/(<\/ul>)<\/p>/g, '$1');
  processed = processed.replace(/<p>(<ol>)/g, '$1');
  processed = processed.replace(/(<\/ol>)<\/p>/g, '$1');
  processed = processed.replace(/<p>(<table>)/g, '$1');
  processed = processed.replace(/(<\/table>)<\/p>/g, '$1');
  
  return processed;
}

function processMarkdownLine(line) {
  let processed = line;
  
  // Headers
  if (processed.startsWith('### ')) {
    return `<h3>${processed.slice(4)}</h3>`;
  }
  if (processed.startsWith('## ')) {
    return `<h2>${processed.slice(3)}</h2>`;
  }
  if (processed.startsWith('# ')) {
    return `<h1>${processed.slice(2)}</h1>`;
  }
  
  // Lists
  if (processed.startsWith('* ')) {
    return `<li>${processed.slice(2)}</li>`;
  }
  if (/^\d+\.\s+/.test(processed)) {
    const text = processed.replace(/^\d+\.\s+/, '');
    return `<li>${text}</li>`;
  }
  
  // Bold and italic
  processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  processed = processed.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Inline code
  processed = processed.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  return processed;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Wrap contiguous list item blocks into <ul> or <ol>
function wrapListBlocks(input, blockDetector, itemRegex, listTag) {
  // Split by double newlines to work with paragraphs/blocks
  const blocks = input.split(/\n\n/);
  const out = blocks.map(block => {
    if (!block.match(itemRegex)) return block;

    // If the block contains at least one list item, transform each matching line
    const lines = block.split('\n');
    let inList = false;
    let buf = '';
    let result = '';

    for (const line of lines) {
      if (itemRegex.test(line)) {
        if (!inList) {
          inList = true;
          buf = '';
        }
        const m = line.match(itemRegex);
        const itemText = listTag === 'ol' && m && m[2] ? m[2] : (m && m[1]) ? m[1] : line.replace(/^\*\s+/, '');
        buf += `<li>${itemText}</li>`;
      } else {
        if (inList) {
          result += `<${listTag}>${buf}</${listTag}>\n`;
          inList = false;
          buf = '';
        }
        result += line + '\n';
      }
    }
    if (inList) {
      result += `<${listTag}>${buf}</${listTag}>`;
    }
    return result.trim();
  });
  return out.join('\n\n');
}

// Detect and render a GFM-style markdown table block to HTML
function renderMarkdownTable(block) {
  const lines = block.split('\n').filter(l => l.trim().length > 0);
  if (lines.length < 2) return null;
  if (!lines[0].trim().startsWith('|')) return null;
  if (!lines[1].trim().startsWith('|')) return null;

  // Parse rows by splitting on pipes, trimming, dropping first/last empty
  const parseRow = (line) => line
    .split('|')
    .map(c => c.trim())
    .filter((_, idx, arr) => !(idx === 0 && arr[idx] === '') && !(idx === arr.length - 1 && arr[idx] === ''));

  const headerCells = parseRow(lines[0]);
  const separatorCells = parseRow(lines[1]);

  // Validate separator row like | --- | :---: | ---: |
  const sepValid = separatorCells.length >= headerCells.length && separatorCells.every(cell => /^:?-{3,}:?$/.test(cell));
  if (!sepValid) return null;

  const headerHtml = headerCells.map(h => `<th>${escapeHtml(h)}</th>`).join('');
  const bodyRows = [];
  for (let i = 2; i < lines.length; i++) {
    const line = lines[i];
    if (!line.trim().startsWith('|')) break;
    const cells = parseRow(line);
    // Allow row to be shorter; missing cells become empty
    const padded = Array.from({ length: headerCells.length }, (_, idx) => cells[idx] || '');
    const cellsHtml = padded.map(c => `<td>${escapeHtml(c).replace(/\n/g, '<br/>')}</td>`).join('');
    bodyRows.push(`<tr>${cellsHtml}</tr>`);
  }

  const tableHtml = `<table><thead><tr>${headerHtml}</tr></thead><tbody>${bodyRows.join('')}</tbody></table>`;
  return tableHtml;
}

export default MarkdownRenderer;
