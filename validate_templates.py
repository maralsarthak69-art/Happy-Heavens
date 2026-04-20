#!/usr/bin/env python
"""
Validate all Django templates for syntax errors and duplicate blocks.
"""
import os
import re
from pathlib import Path

def validate_template(file_path):
    """Validate a single template file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    errors = []
    
    # Check for duplicate seo blocks
    seo_blocks = re.findall(r'{% block seo %}', content)
    if len(seo_blocks) > 1:
        errors.append(f"Duplicate seo blocks found: {len(seo_blocks)} occurrences")
    
    # Check for balanced blocks
    all_blocks = re.findall(r'{% block (\w+) %}', content)
    all_endblocks = re.findall(r'{% endblock', content)
    
    if len(all_blocks) != len(all_endblocks):
        errors.append(f"Unbalanced blocks: {len(all_blocks)} blocks, {len(all_endblocks)} endblocks")
    
    # Check for template syntax in comments (like our original issue)
    comment_blocks = re.findall(r'<!--.*?{% block.*?%}.*?-->', content, re.DOTALL)
    if comment_blocks:
        errors.append(f"Template syntax found in comments: {len(comment_blocks)} occurrences")
    
    return errors

def main():
    """Validate all templates."""
    templates_dir = Path('templates')
    if not templates_dir.exists():
        print("❌ Templates directory not found")
        return
    
    total_files = 0
    total_errors = 0
    
    for html_file in templates_dir.rglob('*.html'):
        total_files += 1
        errors = validate_template(html_file)
        
        if errors:
            total_errors += len(errors)
            print(f"❌ {html_file}:")
            for error in errors:
                print(f"   - {error}")
        else:
            print(f"✅ {html_file}")
    
    print(f"\n📊 Summary: {total_files} files checked, {total_errors} errors found")
    
    if total_errors == 0:
        print("🎉 All templates are valid!")
    else:
        print("⚠️ Please fix the errors above")

if __name__ == '__main__':
    main()