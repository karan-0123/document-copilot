import re
from pathlib import Path
from docling_core.types.doc import DoclingDocument, DocItemLabel, BoundingBox
from docling_core.types.doc.document import ProvenanceItem
from docling.chunking import HybridChunker, HierarchicalChunker


def parse_markdown_to_docling(markdown_path: Path) -> DoclingDocument:
    """Parses local markdown line-by-line to get sections, paragraphs, and page numbers,

    and programmatically builds a DoclingDocument object.
    """
    markdown_content = markdown_path.read_text(encoding="utf-8")
    doc = DoclingDocument(name=markdown_path.stem)
    
    VALID_ITEMS = ["1", "1A", "1B", "1C", "2", "3", "4", "5", "6", "7", "7A", "8", "9", "9A", "9B", "9C", "10", "11", "12", "13", "14", "15", "16"]
    
    current_item = "INTRO"
    current_title = "Introduction"
    current_lines = []
    current_page = 1  # default to page 1
    
    lines = markdown_content.splitlines()
    
    def add_section_to_doc(item_num, title, lines_list):
        # Add heading
        sec_name = f"Item {item_num}. {title}" if item_num != "INTRO" else "Introduction"
        doc.add_heading(text=sec_name, level=1)
        
        # Group lines into paragraphs
        paragraphs = []
        current_p_lines = []
        current_p_page = 1
        
        for line, page in lines_list:
            if line.strip():
                current_p_lines.append(line)
                if page is not None:
                    current_p_page = page
            else:
                if current_p_lines:
                    paragraphs.append({
                        "text": "\n".join(current_p_lines),
                        "page": current_p_page
                    })
                    current_p_lines = []
                    
        if current_p_lines:
            paragraphs.append({
                "text": "\n".join(current_p_lines),
                "page": current_p_page
            })
            
        for p in paragraphs:
            # Add text with page provenance
            bbox = BoundingBox(l=0.0, t=0.0, r=0.0, b=0.0)
            prov = ProvenanceItem(page_no=p["page"], bbox=bbox, charspan=(0, len(p["text"])))
            doc.add_text(label=DocItemLabel.PARAGRAPH, text=p["text"], prov=prov)
            
    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        
        # Check for page numbers: digit on its own line (with empty lines before/after)
        if line_stripped.isdigit() and 1 <= len(line_stripped) <= 3:
            prev_empty = idx == 0 or not lines[idx-1].strip()
            next_empty = idx == len(lines)-1 or not lines[idx+1].strip()
            if prev_empty and next_empty:
                current_page = int(line_stripped)
                continue
        
        # Check for section headers
        m = re.match(
            r'^ITEM\s+(1|1A|1B|1C|2|3|4|5|6|7|7A|8|9|9A|9B|9C|10|11|12|13|14|15|16)\b[.:\s-]*(.*)$',
            line_stripped,
            re.IGNORECASE
        )
        if m:
            item_num = m.group(1).upper()
            title = re.sub(r'[\s|#*_-]+', ' ', m.group(2)).strip()
            
            if re.match(r'^[.,\s]*$', re.sub(r'\d+[A-Z]?', '', title)):
                title = ''
                
            if len(title) >= 3:
                # New section with full title
                if item_num != current_item:
                    add_section_to_doc(current_item, current_title, current_lines)
                    current_item = item_num
                    current_title = title
                    current_lines = []
            else:
                # Check if we transitioned to a new section without a long title on the same line
                is_new = False
                if current_item == "INTRO":
                    is_new = True
                elif current_item in VALID_ITEMS and item_num in VALID_ITEMS:
                    is_new = VALID_ITEMS.index(item_num) > VALID_ITEMS.index(current_item)
                
                if is_new:
                    add_section_to_doc(current_item, current_title, current_lines)
                    current_item = item_num
                    current_title = f"Item {item_num}"
                    current_lines = []
            continue
            
        current_lines.append((line, current_page))
        
    if current_lines:
        add_section_to_doc(current_item, current_title, current_lines)
        
    return doc


def get_chunker(chunker_type: str, max_tokens: int = 500):
    """Returns either a HybridChunker or HierarchicalChunker."""
    if chunker_type.lower() == "hybrid":
        return HybridChunker(max_tokens=max_tokens)
    elif chunker_type.lower() == "hierarchical":
        return HierarchicalChunker()
    else:
        raise ValueError(f"Unknown chunker type: {chunker_type}")


def chunk_document(doc: DoclingDocument, chunker) -> list[dict]:
    """Chunks the DoclingDocument and maps them to structural chunk metadata."""
    chunks = []
    docling_chunks = list(chunker.chunk(doc))
    
    for idx, c in enumerate(docling_chunks):
        # Extract section heading
        section_name = c.meta.headings[0] if c.meta.headings else "Introduction"
        
        # Extract page number (find the last page number in the chunk elements' provenance)
        page_no = None
        if c.meta.doc_items:
            for item in reversed(c.meta.doc_items):
                if item.prov and item.prov[0].page_no is not None:
                    page_no = str(item.prov[0].page_no)
                    break
                    
        chunks.append({
            "chunk_index": idx,
            "text": c.text,
            "page": page_no,
            "section": section_name,
            "token_count": None
        })
        
    return chunks
