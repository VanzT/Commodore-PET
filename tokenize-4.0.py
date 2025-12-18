#!/usr/bin/env python3
"""
PET BASIC 2.0/4.0 Tokenizer
Creates proper tokenized .PRG files for Commodore PET
Supports BASIC 2.0 + BASIC 4.0 disk commands
Matches the format of native PET-saved programs
"""

import sys
import struct

# PET BASIC 2.0 tokens
TOKENS = {
    'END': 0x80, 'FOR': 0x81, 'NEXT': 0x82, 'DATA': 0x83, 'INPUT#': 0x84,
    'INPUT': 0x85, 'DIM': 0x86, 'READ': 0x87, 'LET': 0x88, 'GOTO': 0x89,
    'RUN': 0x8A, 'IF': 0x8B, 'RESTORE': 0x8C, 'GOSUB': 0x8D, 'RETURN': 0x8E,
    'REM': 0x8F, 'STOP': 0x90, 'ON': 0x91, 'WAIT': 0x92, 'LOAD': 0x93,
    'SAVE': 0x94, 'VERIFY': 0x95, 'DEF': 0x96, 'POKE': 0x97, 'PRINT#': 0x98,
    'PRINT': 0x99, 'CONT': 0x9A, 'LIST': 0x9B, 'CLR': 0x9C, 'CMD': 0x9D,
    'SYS': 0x9E, 'OPEN': 0x9F, 'CLOSE': 0xA0, 'GET': 0xA1, 'NEW': 0xA2,
    'TAB(': 0xA3, 'TO': 0xA4, 'FN': 0xA5, 'SPC(': 0xA6, 'THEN': 0xA7,
    'NOT': 0xA8, 'STEP': 0xA9, '+': 0xAA, '-': 0xAB, '*': 0xAC, '/': 0xAD,
    '^': 0xAE, 'AND': 0xAF, 'OR': 0xB0, '>': 0xB1, '=': 0xB2, '<': 0xB3,
    'SGN': 0xB4, 'INT': 0xB5, 'ABS': 0xB6, 'USR': 0xB7, 'FRE': 0xB8,
    'POS': 0xB9, 'SQR': 0xBA, 'RND': 0xBB, 'LOG': 0xBC, 'EXP': 0xBD,
    'COS': 0xBE, 'SIN': 0xBF, 'TAN': 0xC0, 'ATN': 0xC1, 'PEEK': 0xC2,
    'LEN': 0xC3, 'STR$': 0xC4, 'VAL': 0xC5, 'ASC': 0xC6, 'CHR$': 0xC7,
    'LEFT$': 0xC8, 'RIGHT$': 0xC9, 'MID$': 0xCA,
    # BASIC 4.0 additions (disk commands)
    'CONCAT': 0xCC, 'DOPEN': 0xCD, 'DCLOSE': 0xCE, 'RECORD': 0xCF,
    'HEADER': 0xD0, 'COLLECT': 0xD1, 'BACKUP': 0xD2, 'COPY': 0xD3,
    'APPEND': 0xD4, 'DSAVE': 0xD5, 'DLOAD': 0xD6, 'CATALOG': 0xD7,
    'RENAME': 0xD8, 'SCRATCH': 0xD9, 'DIRECTORY': 0xDA,
}

# Sort tokens by length (longest first) to match correctly
SORTED_TOKENS = sorted(TOKENS.items(), key=lambda x: (-len(x[0]), x[0]))

def tokenize_line(line_text):
    """Tokenize a single BASIC line"""
    result = bytearray()
    i = 0
    in_quote = False
    in_rem = False
    
    while i < len(line_text):
        char = line_text[i]
        
        # Handle quotes
        if char == '"':
            in_quote = not in_quote
            result.append(ord(char))
            i += 1
            continue
            
        # Inside quotes or REM, just copy literally
        if in_quote or in_rem:
            result.append(ord(char))
            i += 1
            continue
            
        # Try to match tokens
        matched = False
        for token_name, token_value in SORTED_TOKENS:
            if line_text[i:i+len(token_name)].upper() == token_name:
                # Make sure it's a complete word (not part of variable name)
                # But only for alphabetic tokens, not operators
                if token_name[0].isalpha():
                    next_char_idx = i + len(token_name)
                    if next_char_idx < len(line_text):
                        next_char = line_text[next_char_idx]
                        # If next char is alphanumeric, it's part of a variable name
                        if next_char.isalnum() or next_char in '$%':
                            continue
                        
                result.append(token_value)
                i += len(token_name)
                matched = True
                
                # Skip any spaces immediately after the token
                while i < len(line_text) and line_text[i] == ' ':
                    i += 1
                
                # Check if this was REM
                if token_name == 'REM':
                    in_rem = True
                break
                
        if not matched:
            result.append(ord(char))
            i += 1
            
    return bytes(result)

def create_prg(basic_lines, load_addr=0x0401):
    """Create a tokenized PRG file from BASIC lines"""
    prg = bytearray()
    
    # Add load address (2 bytes, little-endian)
    prg.extend(struct.pack('<H', load_addr))
    
    current_addr = load_addr
    
    for line_num, line_text in basic_lines:
        line_start_offset = len(prg)  # Where this line's pointer is
        
        if line_num <= 50:  # Debug first few lines
            print(f"DEBUG: Line {line_num} starts at offset {line_start_offset}, len(prg)={len(prg)}", file=sys.stderr)
        
        # Reserve space for next line pointer (will fill in later)
        prg.extend([0, 0])
        
        # Add line number (2 bytes, little-endian)
        prg.extend(struct.pack('<H', line_num))
        
        # Tokenize and add line content
        tokenized = tokenize_line(line_text)
        prg.extend(tokenized)
        
        # Add end of line marker
        prg.append(0)
        
        # Calculate next line pointer (points to next line's link address)
        # File offset X maps to memory address (load_addr + X - 2)
        # So next line link will be at file offset len(prg)
        # Which is memory address: load_addr + len(prg) - 2
        next_link_addr = load_addr + len(prg) - 2
        
        if line_num <= 50:  # Debug first few lines
            print(f"DEBUG:   After line: len(prg)={len(prg)}, next_link=${next_link_addr:04X}", file=sys.stderr)
        
        struct.pack_into('<H', prg, line_start_offset, next_link_addr)
    
    # Add end of program marker (two zero bytes)
    prg.extend([0, 0])
    
    return bytes(prg)

def parse_basic_file(filename):
    """Parse a BASIC text file and return list of (line_num, line_text) tuples"""
    lines = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Split line number from rest of line
            parts = line.split(' ', 1)
            if len(parts) < 2:
                continue
                
            try:
                line_num = int(parts[0])
                line_text = parts[1] if len(parts) > 1 else ''
                lines.append((line_num, line_text))
            except ValueError:
                continue
                
    return lines

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: tokenize.py input.bas output.prg")
        sys.exit(1)
        
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    # Parse BASIC file
    lines = parse_basic_file(input_file)
    
    if not lines:
        print("No BASIC lines found in input file")
        sys.exit(1)
        
    # Create PRG
    prg_data = create_prg(lines)
    
    # Write output
    with open(output_file, 'wb') as f:
        f.write(prg_data)
        
    print(f"Created {output_file} ({len(prg_data)} bytes, {len(lines)} lines)")
