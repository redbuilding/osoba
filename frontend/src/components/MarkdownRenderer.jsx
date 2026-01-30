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
  
  // Bold and italic
  processed = processed.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  processed = processed.replace(/\*(.*?)\*/g, '<em>$1</em>');
  
  // Code blocks
  processed = processed.replace(/```(\w+)?\n([\s\S]*?)```/g, (match, lang, code) => {
    return `<pre><code class="language-${lang || ''}">${escapeHtml(code.trim())}</code></pre>`;
  });
  
  // Inline code
  processed = processed.replace(/`([^`]+)`/g, '<code>$1</code>');
  
  // Lists
  processed = processed.replace(/^\* (.+$)/gm, '<li>$1</li>');
  processed = processed.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  
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

export default MarkdownRenderer;
