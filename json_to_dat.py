#!/usr/bin/env python3
"""
Convert MSX ROMs JSON database to Logiqx DAT format
"""

import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
import os
import sys
from datetime import datetime


def prettify_xml(elem):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def create_dat_from_json(json_file, output_file=None, platform_filter=None):
    """
    Convert JSON ROM database to Logiqx DAT format
    
    Args:
        json_file: Path to input JSON file
        output_file: Path to output DAT file (optional, defaults to input_name.dat)
        platform_filter: Only include games from this platform (e.g., 'MSX', 'MSX2')
    """
    
    # Read JSON file
    print(f"Reading JSON file: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Create root element
    root = ET.Element('datafile')
    
    # Create header
    header = ET.SubElement(root, 'header')
    
    name_elem = ET.SubElement(header, 'name')
    if platform_filter:
        name_elem.text = f'{platform_filter} ROMs Database'
    else:
        name_elem.text = 'MSX ROMs Database'
    
    desc_elem = ET.SubElement(header, 'description')
    if platform_filter:
        desc_elem.text = f'{platform_filter} ROM Database'
    else:
        desc_elem.text = data.get('comments', 'MSX and MSX2 ROM Database')
    
    version_elem = ET.SubElement(header, 'version')
    timestamp = data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    version_elem.text = timestamp.split()[0]  # Use date as version
    
    date_elem = ET.SubElement(header, 'date')
    date_elem.text = timestamp
    
    author_elem = ET.SubElement(header, 'author')
    author_elem.text = 'MSX ROM Database'
    
    homepage_elem = ET.SubElement(header, 'homepage')
    homepage_elem.text = 'https://romdb.vampier.net/'
    
    # Process ROMs
    roms = data.get('roms', [])
    
    # Filter by platform if specified
    if platform_filter:
        roms = [r for r in roms if r.get('platform') == platform_filter]
        print(f"Filtered to {len(roms)} games for platform: {platform_filter}")
    else:
        print(f"Processing {len(roms)} games (all platforms)...")
    
    game_count = 0
    rom_count = 0
    
    for rom_entry in roms:
        gamename = rom_entry.get('gamename', 'Unknown')
        year = rom_entry.get('year', '')
        publisher = rom_entry.get('publisher', '')
        platform = rom_entry.get('platform', 'MSX')
        
        hashes = rom_entry.get('hashes', [])
        
        # Create a game element for each hash/file
        for hash_entry in hashes:
            # Use original filename but wrap publisher in parentheses
            original_filename = hash_entry.get('FileName', f"{gamename}.rom")
            
            # If publisher exists and is not already in parentheses, wrap it
            if publisher and publisher in original_filename:
                # Replace " Publisher " with " (Publisher) " keeping proper spacing
                filename = original_filename.replace(f" {publisher} ", f" ({publisher}) ")
                # Also handle case where publisher is before bracket
                if filename == original_filename:  # If not replaced yet
                    filename = original_filename.replace(f" {publisher} [", f" ({publisher}) [")
                # Also handle end of string cases
                if filename == original_filename:  # If still not replaced
                    filename = original_filename.replace(f" {publisher}.", f" ({publisher}).")
            else:
                filename = original_filename
            
            # Final sanitization: replace any remaining "/" in the entire filename
            filename = filename.replace(' / ', ' - ').replace('/', '-')
            
            # TOSEC standard: game name and description should match ROM name (without extension)
            game_name_from_file = filename.rsplit('.', 1)[0]  # Remove .rom extension
            
            game = ET.SubElement(root, 'game')
            game.set('name', game_name_from_file)
            
            desc_elem = ET.SubElement(game, 'description')
            desc_elem.text = game_name_from_file
            
            if year:
                year_elem = ET.SubElement(game, 'year')
                year_elem.text = year
            
            if publisher:
                manufacturer_elem = ET.SubElement(game, 'manufacturer')
                manufacturer_elem.text = publisher
            
            # Add platform as a comment in the game
            comment_elem = ET.SubElement(game, 'comment')
            comment_text = f"Platform: {platform}"
            if hash_entry.get('romtype'):
                comment_text += f" | ROM Type: {hash_entry['romtype']}"
            if hash_entry.get('dump'):
                comment_text += f" | Dump: {hash_entry['dump']}"
            if hash_entry.get('preferred') == 'on':
                comment_text += " | Preferred: Yes"
            comment_elem.text = comment_text
            
            # Add ROM element
            rom_elem = ET.SubElement(game, 'rom')
            rom_elem.set('name', filename)
            
            # Add SHA1 if available
            if hash_entry.get('sha1'):
                rom_elem.set('sha1', hash_entry['sha1'].upper())
            
            # Note: Size, CRC, MD5 are not in the source JSON, so we can't include them
            # These would typically be required for proper DAT files
            rom_elem.set('size', 'unknown')
            
            rom_count += 1
        
        game_count += 1
        if game_count % 100 == 0:
            print(f"  Processed {game_count} games, {rom_count} ROM files...")
    
    print(f"Total: {game_count} games, {rom_count} ROM files")
    
    # Generate output filename if not provided
    if output_file is None:
        base_name = os.path.splitext(json_file)[0]
        output_file = f"{base_name}.dat"
    
    # Write XML file
    print(f"Writing DAT file: {output_file}")
    
    # Create pretty XML with proper DOCTYPE
    xml_string = prettify_xml(root)
    
    # Add DOCTYPE declaration
    xml_lines = xml_string.split('\n')
    doctype = '<!DOCTYPE datafile PUBLIC "-//Logiqx//DTD ROM Management Datafile//EN" "http://www.logiqx.com/Dats/datafile.dtd">'
    
    final_xml = []
    for i, line in enumerate(xml_lines):
        final_xml.append(line)
        if i == 0 and line.startswith('<?xml'):
            final_xml.append(doctype)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(final_xml))
    
    print(f"✓ Conversion complete! DAT file saved to: {output_file}")
    return output_file


def main():
    if len(sys.argv) < 2:
        print("Usage: python json_to_dat.py <input_json_file> [output_dat_file] [--platform PLATFORM]")
        print("\nExample:")
        print("  python json_to_dat.py msxromsdb.json")
        print("  python json_to_dat.py msxromsdb.json output.dat")
        print("  python json_to_dat.py msxromsdb.json --platform MSX")
        print("  python json_to_dat.py msxromsdb.json msx_only.dat --platform MSX")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = None
    platform_filter = None
    
    # Parse arguments
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == '--platform' and i + 1 < len(sys.argv):
            platform_filter = sys.argv[i + 1]
            i += 2
        elif not output_file and not sys.argv[i].startswith('--'):
            output_file = sys.argv[i]
            i += 1
        else:
            i += 1
    
    if not os.path.exists(json_file):
        print(f"Error: File not found: {json_file}")
        sys.exit(1)
    
    try:
        create_dat_from_json(json_file, output_file, platform_filter)
    except Exception as e:
        print(f"Error during conversion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
