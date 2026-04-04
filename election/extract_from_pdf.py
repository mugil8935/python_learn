import re
import csv
from pathlib import Path
import pdfplumber


def extract_parts_from_text(text):
    # find all PartName- occurrences and slice blocks between them
    part_starts = list(re.finditer(r'PartName-(\d+)-', text))
    rows = []
    if not part_starts:
        return rows

    for i, m in enumerate(part_starts):
        start = m.start()
        end = part_starts[i + 1].start() if i + 1 < len(part_starts) else len(text)
        block = text[start:end]

        part_no = int(m.group(1))

        # extract part name: take text after 'PartName-<n>-' up to 'S. No' if present,
        # otherwise up to the first newline. Allow dots in the part name.
        after_header = block[len(m.group(0)):]
        if 'S. No' in after_header:
            part_name = after_header.split('S. No', 1)[0].strip()
        else:
            part_name = after_header.splitlines()[0].strip()
        part_name = part_name.rstrip('.').replace('\n', ' ').strip()

        # part-level total if present
        mtotal = re.search(r'Total\s*:\s*(\d+)', block)
        part_total = int(mtotal.group(1)) if mtotal else None

        # find rows: start with a line beginning with slno, then capture until next slno or Total or PartName
        row_pattern = re.compile(r"^\s*(\d+)\s+(.+?)(?=(?:\n\s*\d+\s)|\n\s*Total\s*:|\n\s*PartName-|$)", re.S | re.M)
        for rmatch in row_pattern.finditer(block):
            slno_str = rmatch.group(1)
            content = rmatch.group(2).strip()
            fullmatch = rmatch.group(0).strip()

            # extract all numbers in the full matched text; last two are electors and votes
            nums = re.findall(r'\d+', fullmatch)
            if len(nums) < 2:
                continue
            slno = int(nums[0])
            total_part_votes = int(nums[-1])
            total_electors = int(nums[-2]) if part_total is None else part_total

            # remove trailing two numbers from the text to get section name
            section = fullmatch
            section = re.sub(r"\s*\d+\s*$", '', section)
            section = re.sub(r"\s*\d+\s*$", '', section)
            # remove leading slno
            section = re.sub(r'^\s*\d+\s*[-–]?\s*', '', section).strip(' -,:')

            # If section looks empty or contains no letters (split across lines in PDF),
            # try to grab following alphabetic lines and append them.
            if not any(c.isalpha() for c in section):
                tail = block[rmatch.end():]
                mtail = re.match(r"\s*([A-Za-z0-9.,()&'\-\s]+?)\s*(?=\n\s*\d+\s|\n\s*Total\s*:|\n\s*PartName-|$)", tail, re.S)
                if mtail:
                    extra = mtail.group(1).strip()
                    if extra:
                        # join with a space and clean commas/newlines
                        section = (section + ' ' + extra).strip(' -,:')

            rows.append((part_no, part_name, slno, section, total_electors, total_part_votes))

    return rows


def main():
    pdf_path = Path(__file__).parent / '82_atu.pdf'
    out_csv = Path(__file__).parent / 'parts_extracted_from_pdf.csv'

    # avoid PermissionError if the file is open by removing or renaming it
    if out_csv.exists():
        try:
            out_csv.unlink()
        except PermissionError:
            out_csv = out_csv.with_name(out_csv.stem + '.new' + out_csv.suffix)

    text = ''
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + '\n'

    rows = extract_parts_from_text(text)

    with out_csv.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['part_no', 'Part name', 'slno', 'section name', 'total electors', 'total part votes'])
        for r in rows:
            writer.writerow(r)

    print('Wrote', out_csv)


if __name__ == '__main__':
    main()
