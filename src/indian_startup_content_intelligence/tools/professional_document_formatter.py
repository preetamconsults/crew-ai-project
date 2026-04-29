from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Type
import re

class ProfessionalDocumentFormatterInput(BaseModel):
    """Input schema for Professional Document Formatter Tool."""
    content: str = Field(..., description="The content brief with markdown-style formatting to convert to professional HTML")

class ProfessionalDocumentFormatter(BaseTool):
    """Tool for converting content briefs into professionally formatted HTML documents."""

    name: str = "Professional Document Formatter"
    description: str = (
        "Converts content briefs with markdown-style formatting into professionally formatted HTML documents. "
        "Supports headers, bold/italic text, bullet points, numbered lists, tables, and applies professional CSS styling. "
        "Output is optimized for copying into Microsoft Word or other document editors."
    )
    args_schema: Type[BaseModel] = ProfessionalDocumentFormatterInput

    def _run(self, content: str) -> str:
        """
        Convert markdown-style content to professionally formatted HTML.
        
        Args:
            content: The content brief with markdown formatting
            
        Returns:
            Complete HTML document with embedded professional CSS styling
        """
        try:
            # Professional CSS styles
            css_styles = """
            <style>
            body {
                font-family: 'Calibri', 'Arial', sans-serif;
                font-size: 11pt;
                line-height: 1.5;
                color: #2c2c2c;
                max-width: 8.5in;
                margin: 1in auto;
                padding: 0.5in;
                background: white;
            }
            
            h1 {
                font-size: 18pt;
                font-weight: bold;
                color: #1f4e79;
                margin-top: 24pt;
                margin-bottom: 12pt;
                border-bottom: 2px solid #1f4e79;
                padding-bottom: 6pt;
            }
            
            h2 {
                font-size: 14pt;
                font-weight: bold;
                color: #2c2c2c;
                margin-top: 18pt;
                margin-bottom: 10pt;
                border-bottom: 1px solid #cccccc;
                padding-bottom: 3pt;
            }
            
            h3 {
                font-size: 12pt;
                font-weight: bold;
                color: #2c2c2c;
                margin-top: 14pt;
                margin-bottom: 8pt;
            }
            
            p {
                margin-bottom: 12pt;
                text-align: justify;
            }
            
            strong {
                font-weight: bold;
                color: #1f4e79;
            }
            
            em {
                font-style: italic;
            }
            
            ul {
                margin-bottom: 12pt;
                padding-left: 20pt;
            }
            
            ol {
                margin-bottom: 12pt;
                padding-left: 20pt;
            }
            
            li {
                margin-bottom: 6pt;
                line-height: 1.4;
            }
            
            table {
                border-collapse: collapse;
                width: 100%;
                margin: 12pt 0;
                border: 1px solid #2c2c2c;
            }
            
            th {
                background-color: #f2f2f2;
                border: 1px solid #2c2c2c;
                padding: 8pt;
                text-align: left;
                font-weight: bold;
                color: #1f4e79;
            }
            
            td {
                border: 1px solid #2c2c2c;
                padding: 8pt;
                vertical-align: top;
            }
            
            tr:nth-child(even) {
                background-color: #f9f9f9;
            }
            
            .section-break {
                margin: 24pt 0;
                border-top: 1px solid #cccccc;
                padding-top: 12pt;
            }
            
            @media print {
                body {
                    margin: 0.5in;
                    padding: 0;
                }
                
                h1 {
                    page-break-after: avoid;
                }
                
                table {
                    page-break-inside: avoid;
                }
            }
            </style>
            """
            
            # Split content into lines for processing
            lines = content.split('\n')
            html_content = []
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip empty lines (but preserve spacing)
                if not line:
                    if html_content and not html_content[-1].endswith('</p>'):
                        html_content.append('<p>&nbsp;</p>')
                    i += 1
                    continue
                
                # Process headers
                if line.startswith('# '):
                    html_content.append(f'<h1>{self._clean_text(line[2:])}</h1>')
                elif line.startswith('## '):
                    html_content.append(f'<h2>{self._clean_text(line[3:])}</h2>')
                elif line.startswith('### '):
                    html_content.append(f'<h3>{self._clean_text(line[4:])}</h3>')
                
                # Process tables
                elif '|' in line and line.count('|') >= 2:
                    table_html, next_i = self._process_table(lines, i)
                    html_content.append(table_html)
                    i = next_i
                    continue
                
                # Process unordered lists
                elif line.startswith('- ') or line.startswith('* '):
                    list_html, next_i = self._process_unordered_list(lines, i)
                    html_content.append(list_html)
                    i = next_i
                    continue
                
                # Process ordered lists
                elif re.match(r'^\d+\.\s', line):
                    list_html, next_i = self._process_ordered_list(lines, i)
                    html_content.append(list_html)
                    i = next_i
                    continue
                
                # Process section breaks
                elif line.strip() == '---' or line.strip() == '***':
                    html_content.append('<div class="section-break"></div>')
                
                # Process regular paragraphs
                else:
                    formatted_text = self._format_inline_text(line)
                    html_content.append(f'<p>{formatted_text}</p>')
                
                i += 1
            
            # Build complete HTML document
            html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Professional Document</title>
    {css_styles}
</head>
<body>
    {''.join(html_content)}
</body>
</html>"""
            
            return html_document
            
        except Exception as e:
            return f"Error formatting document: {str(e)}"
    
    def _clean_text(self, text: str) -> str:
        """Clean and format text content."""
        return self._format_inline_text(text)
    
    def _format_inline_text(self, text: str) -> str:
        """Format inline text with bold, italic, and other styling."""
        # Bold text (**text**)
        text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
        
        # Italic text (*text*)
        text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
        
        # Code text (`text`)
        text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
        
        return text
    
    def _process_table(self, lines, start_index):
        """Process markdown-style table and return HTML."""
        table_lines = []
        i = start_index
        
        # Collect all table lines
        while i < len(lines) and '|' in lines[i]:
            line = lines[i].strip()
            if line and not re.match(r'^\|[\s\-\|:]+\|$', line):  # Skip separator lines
                table_lines.append(line)
            i += 1
        
        if not table_lines:
            return '', start_index + 1
        
        html = ['<table>']
        
        # First line as header
        if table_lines:
            headers = [cell.strip() for cell in table_lines[0].split('|')[1:-1]]
            html.append('<thead><tr>')
            for header in headers:
                html.append(f'<th>{self._format_inline_text(header)}</th>')
            html.append('</tr></thead>')
            
            # Remaining lines as data
            if len(table_lines) > 1:
                html.append('<tbody>')
                for row_line in table_lines[1:]:
                    cells = [cell.strip() for cell in row_line.split('|')[1:-1]]
                    html.append('<tr>')
                    for cell in cells:
                        html.append(f'<td>{self._format_inline_text(cell)}</td>')
                    html.append('</tr>')
                html.append('</tbody>')
        
        html.append('</table>')
        return ''.join(html), i
    
    def _process_unordered_list(self, lines, start_index):
        """Process unordered list and return HTML."""
        html = ['<ul>']
        i = start_index
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('- ') or line.startswith('* '):
                item_text = self._format_inline_text(line[2:])
                html.append(f'<li>{item_text}</li>')
            elif not line:  # Empty line continues the list
                pass
            else:  # Non-list item, end the list
                break
            i += 1
        
        html.append('</ul>')
        return ''.join(html), i
    
    def _process_ordered_list(self, lines, start_index):
        """Process ordered list and return HTML."""
        html = ['<ol>']
        i = start_index
        
        while i < len(lines):
            line = lines[i].strip()
            if re.match(r'^\d+\.\s', line):
                item_text = self._format_inline_text(re.sub(r'^\d+\.\s', '', line))
                html.append(f'<li>{item_text}</li>')
            elif not line:  # Empty line continues the list
                pass
            else:  # Non-list item, end the list
                break
            i += 1
        
        html.append('</ol>')
        return ''.join(html), i