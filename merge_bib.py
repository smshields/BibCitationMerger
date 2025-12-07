import sys
import re
import os

class BibEntry:
    def __init__(self, raw_text):
        self.original_raw = raw_text
        self.cite_type = ""
        self.cite_key = ""
        self.fields = {} 
        self.valid = False
        self._parse()

    def _parse(self):
        """
        Robust parser that doesn't rely on strict regex for the header.
        Finds first '{' and first ',' to determine structure.
        """
        text = self.original_raw.strip()
        
        # 1. Find the opening brace defining the entry
        start_brace = text.find('{')
        if start_brace == -1:
            return 

        # 2. Extract Type
        header_part = text[:start_brace].strip()
        if not header_part.startswith('@'):
            return
        self.cite_type = header_part[1:].strip() 

        # 3. Extract Key (Between '{' and first ',')
        first_comma = text.find(',', start_brace)
        
        if first_comma == -1:
            closing_brace = text.rfind('}')
            if closing_brace > start_brace:
                self.cite_key = text[start_brace+1:closing_brace].strip()
                self.valid = True
                return
            else:
                return 

        self.cite_key = text[start_brace+1:first_comma].strip()
        self.valid = True

        # 4. Extract Body (Fields)
        body_content = text[first_comma+1 : text.rfind('}')]
        self.fields = self._tokenize_fields(body_content)

    def _tokenize_fields(self, content):
        fields = {}
        buffer = []
        key_buffer = []
        parsing_key = True
        brace_count = 0
        in_quote = False
        
        i = 0
        while i < len(content):
            char = content[i]

            if parsing_key:
                if char == '=':
                    parsing_key = False
                elif char.strip() or key_buffer: 
                    key_buffer.append(char)
            else:
                if char == '{': brace_count += 1
                elif char == '}': brace_count -= 1
                elif char == '"':
                    if not (buffer and buffer[-1] == '\\'): in_quote = not in_quote
                
                if char == ',' and brace_count == 0 and not in_quote:
                    key = "".join(key_buffer).strip().lower()
                    val = "".join(buffer).strip()
                    if key: fields[key] = val
                    key_buffer = []
                    buffer = []
                    parsing_key = True
                else:
                    buffer.append(char)
            i += 1
            
        if not parsing_key and key_buffer:
            key = "".join(key_buffer).strip().lower()
            val = "".join(buffer).strip()
            if key: fields[key] = val

        return fields

    def get_comparison_val(self, criteria):
        val = ""
        if criteria == "key":
            val = self.cite_key
        elif criteria == "title":
            val = self.fields.get("title", "")
            if (val.startswith('{') and val.endswith('}')) or \
               (val.startswith('"') and val.endswith('"')):
                val = val[1:-1]
            
        return self._normalize(val)

    def is_exact_match(self, other):
        """
        Checks if two entries are identical in content.
        """
        if self.cite_type.lower() != other.cite_type.lower():
            return False
        if self.cite_key != other.cite_key:
            return False
        # Compare dictionaries (order independent)
        return self.fields == other.fields

    @staticmethod
    def _normalize(text):
        if not text: return ""
        text = text.lower().replace('\\', '')
        text = re.sub(r'[\{\}\[\]"]', '', text)
        return re.sub(r'\s+', '', text)

    def to_string(self):
        if not self.valid: return self.original_raw
        out = f"@{self.cite_type}{{{self.cite_key},\n"
        for k in sorted(self.fields.keys()):
            out += f"  {k} = {self.fields[k]},\n"
        out += "}\n"
        return out


def parse_file(filepath):
    if not os.path.exists(filepath):
        print(f"Error: File {filepath} not found.")
        sys.exit(1)

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        lines = f.readlines()

    entries = []
    
    clean_content = ""
    for line in lines:
        if line.strip().startswith('%'):
            continue
        clean_content += line

    current_block = []
    brace_count = 0
    in_entry = False
    
    i = 0
    while i < len(clean_content):
        char = clean_content[i]
        
        if char == '@' and not in_entry:
            rest_of_line = clean_content[i:].split('\n', 1)[0].lower()
            if rest_of_line.startswith("@string") or rest_of_line.startswith("@comment"):
                eol = clean_content.find('\n', i)
                if eol == -1: break
                i = eol
                continue
            
            in_entry = True
            current_block.append(char)
        
        elif in_entry:
            current_block.append(char)
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                
                if brace_count == 0:
                    raw_entry = "".join(current_block)
                    obj = BibEntry(raw_entry)
                    if obj.valid:
                        entries.append(obj)
                    current_block = []
                    in_entry = False
        i += 1
        
    return entries

def get_input(prompt, options):
    while True:
        val = input(prompt + " ").strip()
        if val in options: return val
        print(f"Invalid input. Options: {options}")

def manual_merge(e1, e2):
    print("\n" + "="*40)
    print("      ENTERING MANUAL FIELD MERGE")
    print("="*40)
    
    # Key Resolution
    if e1.cite_key != e2.cite_key:
        print(f"Conflict in Key: [1] {e1.cite_key} | [2] {e2.cite_key}")
        c = get_input("Select Key:", ['1', '2'])
        final_key = e1.cite_key if c == '1' else e2.cite_key
    else:
        final_key = e1.cite_key

    # Field Resolution
    all_keys = set(e1.fields.keys()).union(e2.fields.keys())
    final_fields = {}

    for k in sorted(all_keys):
        v1 = e1.fields.get(k)
        v2 = e2.fields.get(k)

        if v1 and v2:
            if v1 == v2:
                final_fields[k] = v1
            else:
                print(f"\nConflict in field '{k}':")
                print(f"  [1] {v1}")
                print(f"  [2] {v2}")
                c = get_input("Select:", ['1', '2', '3']) # 3 is skip/delete both
                if c == '1': final_fields[k] = v1
                elif c == '2': final_fields[k] = v2
        elif v1:
            print(f"\nField '{k}' only in First citation: {v1}")
            if get_input("Include? [y/n]:", ['y', 'n']) == 'y': final_fields[k] = v1
        elif v2:
            print(f"\nField '{k}' only in Second citation: {v2}")
            if get_input("Include? [y/n]:", ['y', 'n']) == 'y': final_fields[k] = v2

    new_entry = BibEntry("")
    new_entry.cite_type = e1.cite_type
    new_entry.cite_key = final_key
    new_entry.fields = final_fields
    new_entry.valid = True
    print("\nManual Merge Complete.")
    return new_entry

def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python merge_bib.py <file1.bib> <file2.bib> [output.bib]")
        sys.exit(1)
        
    file1, file2 = args[0], args[1]
    output_file = args[2] if len(args) > 2 else "main.bib"

    if os.path.exists(output_file):
        if get_input(f"File '{output_file}' exists. Overwrite? [y/n]:", ['y','n']) != 'y':
            sys.exit(0)

    print("Reading files...")
    list1 = parse_file(file1)
    list2 = parse_file(file2)
    
    total1 = len(list1)
    total2 = len(list2)
    
    if total1 == 0 and total2 == 0:
        print("Warning: No entries found. Check file formatting.")

    # --- PHASE 1: IDENTIFY CONFLICTS ---
    exact_conflicts = [] # (entry1, entry2) where they are identical
    inexact_conflicts = [] # (entry1, entry2) where they differ
    uniques_from_1 = []
    
    list2_remaining = list2[:] 
    
    for entry1 in list1:
        match_index = -1
        
        for i, entry2 in enumerate(list2_remaining):
            key_match = entry1.get_comparison_val("key") == entry2.get_comparison_val("key")
            title_match = False
            if entry1.get_comparison_val("title"):
                title_match = entry1.get_comparison_val("title") == entry2.get_comparison_val("title")
            
            if key_match or title_match:
                match_index = i
                break
        
        if match_index != -1:
            entry2 = list2_remaining.pop(match_index)
            
            # Check for exact match
            if entry1.is_exact_match(entry2):
                exact_conflicts.append((entry1, entry2))
            else:
                inexact_conflicts.append((entry1, entry2))
        else:
            uniques_from_1.append(entry1)

    uniques_from_2 = list2_remaining
    
    # --- PHASE 2: STRATEGY SELECTION ---
    print(f"\nAnalysis Complete:")
    print(f"File 1 Total: {total1} (Unique: {len(uniques_from_1)})")
    print(f"File 2 Total: {total2} (Unique: {len(uniques_from_2)})")
    print("-" * 30)
    print(f"Exact Matches (Identical): {len(exact_conflicts)}")
    print(f"Field Conflicts (Differences): {len(inexact_conflicts)}")
    print("-" * 30)

    final_list = uniques_from_1 + uniques_from_2
    
    # 2a. Handle Exact Matches
    if exact_conflicts:
        prompt = f"Found {len(exact_conflicts)} Exact Matches. Auto-merge (keep one copy)? [y/n/abort]:"
        choice = get_input(prompt, ['y', 'n', 'abort'])
        
        if choice == 'abort':
            sys.exit(0)
        elif choice == 'y':
            print("Auto-merging exact matches...")
            # Take entry1 from each pair
            for e1, e2 in exact_conflicts:
                final_list.append(e1)
        else:
            # If 'n', treat them as conflicts that need manual review (unlikely but requested option logic)
            print("Moving exact matches to manual review queue.")
            inexact_conflicts.extend(exact_conflicts)

    # 2b. Handle Inexact Conflicts
    if inexact_conflicts:
        print(f"\nProceeding to resolve {len(inexact_conflicts)} Field Conflicts.")
        print("1. Manual Resolve (One by One)")
        print("2. Keep All Non-Duplicates (Discard Conflicts)")
        print("3. Abort")
        
        strategy = get_input("Choice:", ['1', '2', '3'])
        
        if strategy == '3':
            print("Aborted.")
            sys.exit(0)
        elif strategy == '2':
            print("Skipping conflicts...")
        elif strategy == '1':
            for i, (e1, e2) in enumerate(inexact_conflicts):
                print("\n" + "#"*50)
                print(f" CONFLICT {i+1}/{len(inexact_conflicts)}")
                print("#"*50)
                
                print("\n--- ENTRY 1 (File 1) ---")
                print(e1.to_string())
                print("--- ENTRY 2 (File 2) ---")
                print(e2.to_string())
                
                print("-" * 50)
                choice = get_input("Action [1:Take 1, 2:Take 2, 3:Manual Merge, 4:Delete Both]:", ['1', '2', '3', '4'])
                
                if choice == '1': final_list.append(e1)
                elif choice == '2': final_list.append(e2)
                elif choice == '3': final_list.append(manual_merge(e1, e2))
                # 4 is delete both

    # --- PHASE 3: WRITE OUTPUT ---
    print(f"\nWriting {len(final_list)} entries to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in final_list:
            f.write(entry.to_string())
            f.write("\n")
            
    print("Done.")

if __name__ == "__main__":
    main()