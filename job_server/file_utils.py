import gzip
import io
from typing import Tuple

import pandas as pd
import numpy as np
from fastapi import UploadFile


def infer_data_type(val):
    if isinstance(val, np.int64):
        return 'INTEGER'
    elif isinstance(val, float):
        return 'DECIMAL'
    else:
        return 'TEXT'

def find_dupe_cols(header, is_csv, panda_header):
    if is_csv:
        header_list = header.split(',')
    else:
        header_list = header.split('\t')

    header_list = [col.replace('"', '').rstrip() for col in header_list]
    renamed_columns = [col for col in panda_header if col not in header_list]
    return renamed_columns

def infer_delimiter(file_content: io.StringIO, max_lines: int = 10) -> str:
    """
    Infer delimiter from file content using csv.Sniffer.

    Args:
        file_content: StringIO object containing file data
        max_lines: Number of lines to sample for detection

    Returns:
        Detected delimiter (',' or '\t')

    Raises:
        ValueError: If delimiter cannot be detected or is not comma/tab
    """
    import csv

    # Save current position
    pos = file_content.tell()

    try:
        # Read sample for detection
        sample_lines = []
        file_content.seek(0)
        for _ in range(max_lines):
            line = file_content.readline()
            if not line:
                break
            sample_lines.append(line)

        # Reset to start
        file_content.seek(0)

        # Filter out trailing empty lines
        while sample_lines and not sample_lines[-1].strip():
            sample_lines.pop()

        if not sample_lines:
            raise ValueError("Empty file")

        sample = ''.join(sample_lines)

        # Primary approach: Use csv.Sniffer to detect delimiter
        # Sniffer properly handles quoted fields
        try:
            sniffer = csv.Sniffer()
            dialect = sniffer.sniff(sample, delimiters=',\t')
            detected_delimiter = dialect.delimiter

            # Validate: only support comma and tab
            if detected_delimiter not in [',', '\t']:
                raise ValueError(f"Unsupported delimiter '{detected_delimiter}' detected. Only comma and tab are supported.")

            return detected_delimiter

        except (csv.Error, Exception):
            # Fallback: Use pandas auto-detection
            try:
                # Test both delimiters to see which produces more columns
                comma_df = pd.read_csv(io.StringIO(sample), sep=',', nrows=2)
                tab_df = pd.read_csv(io.StringIO(sample), sep='\t', nrows=2)

                # Compare number of columns
                if len(tab_df.columns) > len(comma_df.columns):
                    return '\t'
                elif len(comma_df.columns) > 1:
                    return ','
                else:
                    # Check first non-empty line for delimiters
                    for line in sample_lines:
                        if line.strip():
                            if '\t' in line:
                                return '\t'
                            elif ',' in line:
                                return ','
                    # Single column file, default to comma
                    return ','

            except Exception as e:
                # Last resort: check first non-empty line for presence of delimiters
                for line in sample_lines:
                    if line.strip():
                        if '\t' in line:
                            return '\t'
                        elif ',' in line:
                            return ','
                # Single column file, default to comma
                return ','

    finally:
        # Restore original position
        file_content.seek(pos)

async def parse_file(file_content, file_name: str = None, delimiter: str = None) -> pd.DataFrame:
    """
    Parse delimited file with optional delimiter inference.

    Args:
        file_content: File content as StringIO
        file_name: Optional filename (for backward compatibility)
        delimiter: Optional explicit delimiter. If None, will be inferred from content

    Returns:
        Parsed DataFrame

    Raises:
        ValueError: If file cannot be parsed
    """
    if delimiter:
        # Explicit delimiter provided
        return pd.read_csv(file_content, sep=delimiter)

    # Infer delimiter from content
    detected_delimiter = infer_delimiter(file_content)
    return pd.read_csv(file_content, sep=detected_delimiter)


async def is_gzip(stream: bytes) -> bool:
    return stream.startswith(b'\x1f\x8b')


async def decompress_gzip(stream: bytes) -> bytes:
    with gzip.GzipFile(fileobj=io.BytesIO(stream), mode='rb') as gz:
        return gz.read()


async def sample_file(lines: list) -> Tuple[io.StringIO, str]:
    sample = ''
    sample_size = min(10, len(lines))
    for line in lines[:sample_size]:
        line_content = line if isinstance(line, str) else line.decode('utf-8')
        if line_content == '\r':
            break
        sample += line_content + '\n'
    file_name = lines[1].decode('utf-8').split(';')[2].split('=')[1].strip().replace("\"", "")
    return io.StringIO(sample), file_name


async def get_text_sample(file: UploadFile) -> list:
    text_bytes = b""
    while True:
        chunk = await file.read(2048)
        if not chunk:
            break
        text_bytes += chunk

    lines = []
    text_stream = io.StringIO(text_bytes.decode('utf-8'))
    try:
        line = text_stream.readline()
        while line:
            lines.append(line.rstrip('\n'))
            line = text_stream.readline()
    except EOFError:
        pass

    return lines[:-1]


async def get_compressed_sample(file: UploadFile) -> list:
    compressed_bytes = b""
    while True:
        chunk = await file.read(2048)
        if not chunk:
            break
        compressed_bytes += chunk

    lines = []
    with gzip.open(io.BytesIO(compressed_bytes), 'rt') as f:
        try:
            line = f.readline()
            while line:
                lines.append(line.rstrip('\n'))
                line = f.readline()
        except EOFError:
            pass
    # last line might not be a full line
    return lines[:-1]


def validate_bed_line(line: str, line_number: int) -> dict:
    """Validate a single BED file line and return validation results.
    
    Args:
        line: The line to validate
        line_number: Line number for error reporting
        
    Returns:
        dict: Validation result with 'valid', 'errors', and 'warnings' keys
    """
    result = {
        'valid': True,
        'errors': [],
        'warnings': []
    }
    
    # Skip empty lines and comment lines
    line = line.strip()
    if not line or line.startswith('#') or line.startswith('track') or line.startswith('browser'):
        return result
    
    # Split on tab (BED files should be tab-separated)
    fields = line.split('\t')
    
    # Clean up quoted fields (remove quotes if present)
    fields = [field.strip('"').strip("'").strip() for field in fields]
    
    # BED files require at least 3 fields: chromosome, start, end
    if len(fields) < 3:
        result['valid'] = False
        result['errors'].append(f"Line {line_number}: BED format requires at least 3 fields (chromosome, start, end), found {len(fields)}")
        return result
    
    chrom, start_str, end_str = fields[0], fields[1], fields[2]
    
    # Validate chromosome format - must be a valid chromosome identifier
    if not chrom:
        result['valid'] = False
        result['errors'].append(f"Line {line_number}: Chromosome field cannot be empty")
        return result
    
    # Check if chromosome looks like a valid chromosome
    valid_chrom = False
    if chrom.startswith('chr'):
        chrom_num = chrom[3:]
        if chrom_num.isdigit() or chrom_num in ['X', 'Y', 'M', 'MT']:
            valid_chrom = True
    elif chrom.isdigit() or chrom in ['X', 'Y', 'M', 'MT']:
        valid_chrom = True
    
    if not valid_chrom:
        result['valid'] = False
        result['errors'].append(f"Line {line_number}: Invalid chromosome '{chrom}'. Expected format: 'chr1', '1', 'X', 'Y', 'M', 'MT', etc.")
        return result
    
    # Validate start position - must be integer and >= 1
    try:
        start = int(start_str)
        if start < 1:
            result['valid'] = False
            result['errors'].append(f"Line {line_number}: Start position must be >= 1, found: {start}")
            return result
    except ValueError:
        result['valid'] = False
        result['errors'].append(f"Line {line_number}: Start position must be an integer, found: '{start_str}'")
        return result
    
    # Validate end position - must be integer and > start position
    try:
        end = int(end_str)
        if end < 1:
            result['valid'] = False
            result['errors'].append(f"Line {line_number}: End position must be >= 1, found: {end}")
            return result
        elif end <= start:
            result['valid'] = False
            result['errors'].append(f"Line {line_number}: End position ({end}) must be greater than start position ({start})")
            return result
    except ValueError:
        result['valid'] = False
        result['errors'].append(f"Line {line_number}: End position must be an integer, found: '{end_str}'")
        return result
    
    # For genomic annotation files, we don't need to validate optional BED fields
    # as they can contain various types of annotation data
    # Only the first 3 fields (chromosome, start, end) are strictly required
    
    return result


def validate_bed_content(lines: list) -> dict:
    """Validate BED file content and return comprehensive validation results.
    
    Args:
        lines: List of lines from the BED file
        
    Returns:
        dict: Validation results with statistics and errors/warnings
    """
    validation_result = {
        'valid': True,
        'total_lines': len(lines),
        'data_lines': 0,
        'header_lines': 0,
        'empty_lines': 0,
        'errors': [],
        'warnings': [],
        'sample_regions': [],
        'chromosomes': set(),
        'min_fields': float('inf'),
        'max_fields': 0
    }
    
    data_line_count = 0
    
    for i, line in enumerate(lines, 1):
        line = line.strip()
        
        # Count different line types
        if not line:
            validation_result['empty_lines'] += 1
            continue
        elif line.startswith('#') or line.startswith('track') or line.startswith('browser'):
            validation_result['header_lines'] += 1
            continue
        
        # If this looks like a header row with non-numeric positions, skip and count as header
        parts = [p.strip('"').strip("'").strip() for p in line.split('\t')]
        if len(parts) >= 3:
            # If both position columns aren't integers, treat as header
            try:
                int(parts[1])
                int(parts[2])
            except Exception:
                validation_result['header_lines'] += 1
                continue
        
        # This is a data line
        data_line_count += 1
        validation_result['data_lines'] = data_line_count
        
        # Validate individual line
        line_result = validate_bed_line(line, i)
        
        if not line_result['valid']:
            validation_result['valid'] = False
            validation_result['errors'].extend(line_result['errors'])
        
        validation_result['warnings'].extend(line_result['warnings'])
        
        # Collect statistics from valid lines
        fields = line.split('\t')
        field_count = len(fields)
        validation_result['min_fields'] = min(validation_result['min_fields'], field_count)
        validation_result['max_fields'] = max(validation_result['max_fields'], field_count)
        
        if len(fields) >= 3:
            chrom = fields[0]
            validation_result['chromosomes'].add(chrom)
            
            # Store sample regions (first 10 valid lines for preview)
            if len(validation_result['sample_regions']) < 10:
                try:
                    start, end = int(fields[1]), int(fields[2])
                    name = fields[3] if len(fields) > 3 and fields[3] else f"region_{data_line_count}"
                    validation_result['sample_regions'].append({
                        'chromosome': chrom,
                        'start': start,
                        'end': end,
                        'name': name,
                        'length': end - start
                    })
                except (ValueError, IndexError):
                    pass
    
    # Final validation checks
    if validation_result['data_lines'] == 0:
        validation_result['valid'] = False
        validation_result['errors'].append("No valid BED data lines found")
    
    if validation_result['min_fields'] == float('inf'):
        validation_result['min_fields'] = 0
    
    # Convert chromosomes set to sorted list for JSON serialization
    validation_result['chromosomes'] = sorted(list(validation_result['chromosomes']))
    
    return validation_result
