import re
import csv
from pathlib import Path
import pdfplumber


def extract_polling_data(pdf_path):
    """
    Extract polling station data from PDF.
    Handles edge cases like:
    - Dots in part names (e.g., "c.s.v.")
    - Multi-line section names
    - Varying formatting
    """
    rows = []
    
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ''
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + '\n'
    
    # Pattern to find part numbers and names
    # Matches: PartName-<number>-<name until S. No or newline>
    part_pattern = re.compile(
        r'PartName-(\d+)-([^\n]+?)(?=\nS\.\s*No|$)',
        re.IGNORECASE
    )
    
    # Find all parts
    part_matches = list(part_pattern.finditer(full_text))
    
    for part_idx, part_match in enumerate(part_matches):
        part_no = int(part_match.group(1))
        part_name = part_match.group(2).strip()
        
        # Handle dots in part name - preserve them
        part_name = part_name.replace('\n', ' ').strip()
        
        # Get the block for this part (from its start to next part or end)
        part_start = part_match.start()
        part_end = part_matches[part_idx + 1].start() if part_idx + 1 < len(part_matches) else len(full_text)
        part_block = full_text[part_start:part_end]
        
        # Extract total electors for this part (from "Total :" line)
        total_match = re.search(r'Total\s*:\s*(\d+)', part_block)
        total_electors = int(total_match.group(1)) if total_match else None
        
        # Find all serial numbers and their data
        # Pattern: line starting with digit(s), then content, then numbers at end
        # Handle multi-line section names by looking ahead
        slno_pattern = re.compile(
            r'^(\d+)\s+(.+?)$',
            re.MULTILINE
        )
        
        for slno_match in slno_pattern.finditer(part_block):
            slno = int(slno_match.group(1))
            content_line = slno_match.group(2).strip()
            
            # Extract numbers from the content line
            numbers = re.findall(r'\d+', content_line)
            
            # Typically: last number is votes, second-to-last is electors (or use part total)
            if len(numbers) >= 1:
                total_part_votes = int(numbers[-1])
                
                # If we have at least 2 numbers, second-to-last is electors
                if len(numbers) >= 2:
                    electors = int(numbers[-2])
                else:
                    electors = total_electors if total_electors else None
                
                # Extract section name by removing the numbers from the end
                section_name = re.sub(r'\s*\d+\s*$', '', content_line).strip()
                section_name = re.sub(r'\s*\d+\s*$', '', section_name).strip()
                
                # Remove leading slno if present
                section_name = re.sub(r'^\d+\s*[-–]?\s*', '', section_name).strip()
                
                # Clean up section name - preserve dots
                section_name = re.sub(r'[,:]$', '', section_name).strip()
                
                # Handle case where section name might be split across lines
                if not section_name or not any(c.isalpha() for c in section_name):
                    # Look for text on the next line(s)
                    tail_start = slno_match.end()
                    remaining = part_block[tail_start:]
                    tail_match = re.match(
                        r'\s*\n\s*([A-Za-z0-9.,()&\'\-\s]+?)(?=\n\d+\s|\nTotal\s*:|$)',
                        remaining,
                        re.MULTILINE
                    )
                    if tail_match:
                        extra_text = tail_match.group(1).strip()
                        if extra_text and any(c.isalpha() for c in extra_text):
                            section_name = (section_name + ' ' + extra_text).strip()
                            section_name = re.sub(r'[,:]$', '', section_name).strip()
                
                if section_name and electors:
                    rows.append([part_no, part_name, slno, section_name, electors, total_part_votes])
    
    return rows


def main():
    pdf_path = Path(__file__).parent / '82_atu.pdf'
    output_csv = Path(__file__).parent / '82_final.csv'
    
    # Extract data
    rows = extract_polling_data(pdf_path)
    
    # Write to CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['part_no', 'Part name', 'slno', 'section name', 'total electors', 'total part votes'])
        writer.writerows(rows)
    
    print(f'Successfully extracted {len(rows)} rows to {output_csv}')
    print(f'Sample rows:')
    for row in rows[:5]:
        print(row)


if __name__ == '__main__':
    main()
