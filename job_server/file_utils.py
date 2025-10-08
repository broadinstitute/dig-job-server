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

async def parse_file(file_content, file_name) -> pd.DataFrame:
    if '.csv' in file_name:
        return pd.read_csv(file_content)
    elif '.tsv' in file_name:
        return pd.read_csv(file_content, sep='\t')
    else:
        raise ValueError("Unsupported file format")


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
