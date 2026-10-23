"""
Nazi Zombies: Portable QuakeC CRC generator

Takes input .CSV files and outputs an FTEQCC-compilable
QuakeC struct with its contents, always assumes the first
entry should be IBM 3740 CRC16 hashed, adding its length
as an entry as well, for collision detection.
"""

import argparse
import pandas
import sys
import os
from fastcrc import crc16
from colorama import Fore, Style
from dataclasses import dataclass

args = {}
struct_fields = []
original_lengths = []
original_names = []

COL_BLUE = Fore.BLUE
COL_RED = Fore.RED
COL_YEL = Fore.YELLOW
COL_GREEN = Fore.GREEN
COL_NONE = Style.RESET_ALL

ITYPE_FLOAT = 0
ITYPE_STRING = 1
ITYPE_CRC = 2

@dataclass
class StructField:
    '''
    Class for fields that are added to the QuakeC struct.
    '''
    name: str
    item_type: int = ITYPE_FLOAT

def write_qc_file(csv_data):
    '''
    Writes the data obtained into an FTEQCC-compilable
    struct.
    '''
    with open(args['output_file'], 'w') as output:
        # Define the struct.
        output.write('var struct {\n')

        # Write out all of it's types..
        for fields in struct_fields:
            if fields.item_type == ITYPE_STRING:
                output.write('string ')
            else:
                output.write('float ')

            output.write(f'{fields.name};\n')

        # Close the struct.
        output.write('}')

        # Now, the name of it
        struct_name = args['struct_name']
        output.write(f'{struct_name}[]=')
        output.write('{\n')

        # We can begin writing the actual data..
        value_counter = 0
        for value in csv_data.values:
            output.write('{')
            entry_counter = 0
            for entry in value:
                if struct_fields[entry_counter].item_type == ITYPE_STRING:
                    # NZP-M9 FIX: Robustes Escaping für QuakeC-Strings.
                    safe = str(entry).replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ').replace('\r', '')
                    output.write(f'"{safe}",')
                else:
                    output.write(f'{entry},')
                entry_counter += 1

            # Write the length of the first entry
            output.write(str(original_lengths[value_counter]))

            # Close entry, add comma if not the last..
            output.write('}')
            if value_counter + 1 < len(csv_data.values):
                output.write(',')

            # NZP-M9 FIX: Kommentar auf 100 Zeichen begrenzen, Zeilenumbrüche entfernen.
            safe_comment = str(original_names[value_counter]).replace('\n', ' ').replace('\r', '')[:100]
            output.write(f' // {safe_comment}')

            output.write('\n')

            value_counter += 1

        # End struct!
        output.write('};\n')

def create_qc_structfields(csv_data):
    '''
    Parses the .CSV data to create new StructField
    entries given the .CSV specific requirements.
    '''
    global struct_fields

    column_count = 0
    for column in csv_data.columns:
        # Assume first entry is what we always want
        # to hash, append _crc to it, too.
        if column_count == 0:
            item_type = ITYPE_CRC
            item_name = column + '_crc'
        else:
            item_type = ITYPE_STRING
            item_name = column
        struct_fields.append(StructField(item_name, item_type))
        column_count += 1

    # Always append a field that will store the
    # length of the unhashed-CRC.
    struct_fields.append(StructField('crc_strlen', ITYPE_FLOAT))

def generate_qc_file(csv_data):
    '''
    Calls for population of StructFields and prompts
    for writing the .QC file output.
    '''
    create_qc_structfields(csv_data)
    write_qc_file(csv_data)

def read_csv_data():
    '''
    Parses the input_file .CSV, hashes the first column,
    sorts in ascending order and returns the new DataFrame.

    NZP-M9 FIX (Oct 2026):
    - pandas 2.0+ blockiert in-place Zuweisung von int in str-dtypes.
    - Moderne pandas-Versionen iterieren bei `for x in df.values` über
      KOPIEN, wodurch die alten CRC-Werte nie geschrieben wurden und der
      QuakeC-Compiler später an Zeilen wie `misc/buy.wav` scheiterte.
    - Wir bauen den DataFrame daher komplett neu auf.
    '''
    global original_lengths, original_names

    # Alles als String einlesen, damit die Originalreihenfolge stabil bleibt.
    csv_data = pandas.read_csv(args['input_file'], dtype=str, keep_default_na=False)

    n = len(csv_data)
    columns = list(csv_data.columns)

    # Originalreihenfolge merken (Index -> Originalstring).
    orig_by_index = {i: str(csv_data.iloc[i, 0]) for i in range(n)}

    # CRC-Werte berechnen.
    crc_values = [int(crc16.ibm_3740(str.encode(orig_by_index[i]))) for i in range(n)]

    # Neues DataFrame aufbauen: Spalte 0 = int-CRCs, Rest = Strings.
    new_data = {columns[0]: crc_values}
    for col_idx, col_name in enumerate(columns[1:], start=1):
        new_data[col_name] = [str(csv_data.iloc[i, col_idx]) for i in range(n)]

    new_dataframe = pandas.DataFrame(new_data)
    # Originalreihenfolge als Index festhalten, damit `sort_values` sie uns nicht zerstört.
    new_dataframe.index = csv_data.index

    # Aufsteigend nach CRC sortieren.
    sorted_dataframe = new_dataframe.sort_values(columns[0])

    # Originalnamen und -längen passend zum sortierten Index ordnen.
    original_lengths = [len(orig_by_index[i]) for i in sorted_dataframe.index]
    original_names = [orig_by_index[i] for i in sorted_dataframe.index]

    return sorted_dataframe

def fetch_cli_arguments():
    '''
    Initiates ArgParser with all potential command line arguments.
    '''
    global args
    parser = argparse.ArgumentParser(description='IBM 3740 CRC16 hash generator in FTE QuakeC-readable data structure.')
    parser.add_argument('-i', '--input-file',
                        help='.CSV input file to parse.', required=True)
    parser.add_argument('-o', '--output-file',
                        help='File name for generated .QC file.', default='hashes.qc')
    parser.add_argument('-n', '--struct-name',
                        help='Name of the struct generated.', default='asset_conversion_table')
    args = vars(parser.parse_args())

def main():
    fetch_cli_arguments()

    if not os.path.isfile(args['input_file']):
        print(f'{COL_RED}Error{COL_NONE}: Input .CSV file does not exist. Exiting.')
        sys.exit()

    csv_data = read_csv_data()
    generate_qc_file(csv_data)

if __name__ == '__main__':
    main()
