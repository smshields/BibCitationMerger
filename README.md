# BibCitationMerger
A dependency-free, short Python script to merge .bib files into a single file. It removes any duplicates following a somewhat standard merge procedure, providing the user prompts on how a given duplicate cite should be merged into the final list.

# Usage
To merge files:
```
python merge_bib.py input1.bib input2.bib output.bib
```
To deduplicate citations:
```
python merge_bib.py input1.bib
```

# LLM Disclosure
This tool was developed in part using Gemini 3.0
