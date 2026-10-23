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
    Parses the input_file .CSV into a Pandas dictionary,
    performs the hashing on the first indexes, and sorts
    in ascending order.
    '''
    global original_lengths, original_names
    csv_data = pandas.read_csv(args['input_file'])

    # Grab every value before we overwrite column 0
    for value in csv_data.values:
        original_lengths.append(len(str(value[0])))
        original_names.append(str(value[0]))

    # NZP-M9 FIX: 'for value in csv_data.values' iteriert über KOPIEN.
    # Frühere Versionen haben die CRC-Hashes nie in die DataFrame geschrieben,
    # was QuakeC-Syntaxfehler bei Zeilen wie 'misc/buy.wav' ausgelöst hat.
    # Direkte Zuweisung per iloc behebt das.
    for i in range(len(csv_data)):
        original_value = csv_data.iloc[i, 0]
        csv_data.iloc[i, 0] = int(crc16.ibm_3740(str.encode(str(original_value))))

    # Now order everything by ascending order
    csv_data = csv_data.sort_values(csv_data.columns[0])
    original_lengths = [original_lengths[i] for i in csv_data.index]
    original_names = [original_names[i] for i in csv_data.index]

    return csv_data

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
