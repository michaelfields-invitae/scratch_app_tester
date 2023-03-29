import argparse
import logging
import os
from typing import List

import xlrd
import editpyxl
# need to include these lines because by default editpyxl logs a warning to stdout every time a cell's value is updated
editpyxl_logger = logging.getLogger("editpyxl")
editpyxl_logger.disabled = True

from AMPPanelDesignLib.Enums import GSPType
from templates.ProductInsertTemplateFiles import IDTOrderFormTemplateFiles


class GSPInfo:
    def __init__(self, gsp: GSPType, primer_name: str, sequence: str, component_quantity: float, mix_volume: float):
        self.gsp: GSPType = gsp
        self.primer_name: str = primer_name
        self.sequence: str = sequence
        self.component_quantity: float = component_quantity
        self.mix_volume: float = mix_volume


def _extract_primer_info(xls_file_path: str) -> (List[GSPInfo], List[GSPInfo]):
    workbook = xlrd.open_workbook(xls_file_path)
    sheet = workbook.sheet_by_index(0)

    gsp1_info = []
    gsp2_info = []
    for row_index in range(6, sheet.nrows):
        row = sheet.row(row_index)
        primer_name: str = str(row[2].value)
        sequence: str = str(row[3].value)
        quantity: float = float(row[4].value)
        if quantity == 0:
            continue
        mix_volume: float = float(row[5].value)
        if primer_name.casefold().endswith("_gsp1"):
            gsp1_info.append(GSPInfo(gsp=GSPType.GSP1, primer_name=primer_name, sequence=sequence,
                                     component_quantity=quantity, mix_volume=mix_volume))
        elif primer_name.casefold().endswith("_gsp2"):
            gsp2_info.append(GSPInfo(gsp=GSPType.GSP2, primer_name=primer_name, sequence=sequence,
                                     component_quantity=quantity, mix_volume=mix_volume))
        else:
            raise Exception(f"Could not determine GSP type from primer name ({primer_name}) on line "
                            f"{row_index+1} of {xls_file_path}")

    return gsp1_info, gsp2_info


def _adjust_gsp_info(primer_list: List[GSPInfo], scale: float, concentration: float) -> List[GSPInfo]:
    min_gsp_mass = min([gsp.component_quantity for gsp in primer_list])
    adjusted_gsp_info = []
    sum_adjusted_mass = 0
    for primer in primer_list:
        adjusted_mass = float(scale * primer.component_quantity / min_gsp_mass)
        if adjusted_mass > 225:
            raise Exception()
        sum_adjusted_mass += adjusted_mass
        adjusted_gsp_info.append(GSPInfo(gsp=primer.gsp, primer_name=primer.primer_name, sequence=primer.sequence,
                                         component_quantity=round(adjusted_mass, 3), mix_volume=primer.mix_volume))
    adjusted_mix_volume = round(float(sum_adjusted_mass / (float(concentration / 1000))), 1)
    for primer in adjusted_gsp_info:
        primer.mix_volume = adjusted_mix_volume
    return adjusted_gsp_info


def _write_idt_order_form(output_file_path: str, primer_list: List[GSPInfo], pool_id: str, mix_buffer: str) -> None:
    order_form = editpyxl.Workbook()
    order_form.open(IDTOrderFormTemplateFiles.idt_order_form_template_file)
    sheet = order_form["Sheet1"]
    primer_count = len(primer_list)
    gsp_number = primer_list[0].gsp.name[-1]
    pool_part_number = f"AD{pool_id}-{gsp_number}"

    row_number = 36
    for primer in primer_list:
        if primer_count < 240 and primer.mix_volume < 24000:
            pool_name = "Archer Bulk Pool"
            if primer.component_quantity > 60:
                component = 'Archer 225nm Oligo'
                #price = 48.25
            elif primer.component_quantity > 30:
                component = 'Archer 60nm Oligo'
                #price = 19.8
            elif primer.component_quantity > 12:
                component = 'Archer 30nm Oligo'
                #price = 11.95
            else:
                component = 'Archer 12nm Oligo'
                #price = 5.42
        else:
            pool_name = "Archer Large Bulk Pool"
            if primer.component_quantity > 60:
                component = 'Archer 225nm Oligo - Large Pool'
                #price = 48.25
            elif primer.component_quantity > 30:
                component = 'Archer 60nm Oligo - Large Pool'
                #price = 19.8
            elif primer.component_quantity > 12:
                component = 'Archer 30nm Oligo - Large Pool'
                #price = 11.95
            else:
                component = 'Archer 12nm Oligo - Large Pool'
                #price = 5.42
        sheet.cell(row=row_number, column=1).value = pool_name
        sheet.cell(row=row_number, column=2).value = pool_part_number
        sheet.cell(row=row_number, column=3).value = primer.primer_name
        sheet.cell(row=row_number, column=4).value = primer.sequence
        sheet.cell(row=row_number, column=5).value = component
        sheet.cell(row=row_number, column=6).value = "Standard Desalting"
        sheet.cell(row=row_number, column=7).value = "Volume and Quantity"
        sheet.cell(row=row_number, column=8).value = primer.component_quantity
        sheet.cell(row=row_number, column=9).value = primer.mix_volume
        sheet.cell(row=row_number, column=10).value = mix_buffer
        # we are disabling calculating and writing the primer price via the script and instead letting the Excel formula
        # in column K of the IDT order form template perform the calculation instead.
        # uncomment this line and all the #price = X lines above if we ever want to make the script perform the price
        # calculation instead.
        #sheet.cell(row=row_number, column=11).value = price
        row_number += 1
    order_form.save(output_file_path)


def confirm_order_form_generation(primer_list: List[GSPInfo]) -> bool:
    gsp_number = primer_list[0].gsp.name[-1]
    abort = False
    if any([primer for primer in primer_list if primer.component_quantity > 225]):
        print(f"Your max GSP{gsp_number} mass is larger than 225 nmol. Try decreasing your GSP{gsp_number} scale")
        abort = True

    if any([primer for primer in primer_list if primer.mix_volume > 55000]):
        print(f"Your GSP{gsp_number} mix volume is larger than 55mL. Try decreasing your GSP{gsp_number} scale")
        abort = True

    if abort:
        return False

    if len(primer_list) > 550:
        while True:
            print(f"Your GSP{gsp_number} order has too many (>550) primers and must be broken into multiple pools.")
            answer = input(f"Do you want to generate the GSP{gsp_number} IDT order form anyway? (Y/N):")
            if answer.casefold() in ("y", "yes"):
                return True
            elif answer.casefold() in ("n", "no"):
                return False
            else:
                print("\nUnrecognized input. Please enter Y or N")
    else:
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="IDT Order Form Generator")
    parser.add_argument("-i", "--input", required=True, type=str, default=None,
                        help="Input file")
    parser.add_argument("-o", "--output-dir", required=True, type=str,
                        help="Output directory path. Defaults to current working directory. "
                             "Will create one sub-directory per panel configuration file.")
    parser.add_argument("-s", "--scale", required=False, nargs="+", default=[12, 12],
                        help="Space delimited list of base scales (nmol) for GSP1 and GSP2 oligos, respectively. "
                             "It is recommended you use either 12 or 30.")
    parser.add_argument("-c", "--concentration", required=False, nargs='+', default=[100, 100],
                        help="space delimited list of the pool concentrations (uM) for GSP1 and GSP2, respectively. "
                             "Usually these are set at 100uM, for all GLI parts, for example.")
    parser.add_argument("-b", "--buffer", required=False, type=str, default='Water',
                        help="In what buffer would you like your oligos dissolved? Options = 'Tris' or 'Water'. "
                             "Default is Tris. Output file will say either '10 mM Tris' (or) 'RNase Free Water'")

    args = parser.parse_args()
    input_file = args.input
    output_directory = args.output_dir
    gsp1_scale = float(args.scale[0])
    gsp2_scale = float(args.scale[1])
    gsp1_concentration = float(args.concentration[0])
    gsp2_concentration = float(args.concentration[1])
    if args.buffer.casefold() == "tris":
        mix_buffer = "10 mM Tris"
    elif args.buffer.casefold() == "water":
        mix_buffer = "RNase Free Water"
    else:
        raise Exception(f"Unrecognized buffer type: {args.buffer}")

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    pool_id = os.path.basename(input_file).split("_")[0]

    gsp1_list, gsp2_list = _extract_primer_info(input_file)

    gsp1_list = _adjust_gsp_info(primer_list=gsp1_list, scale=gsp1_scale, concentration=gsp1_concentration)
    gsp2_list = _adjust_gsp_info(primer_list=gsp2_list, scale=gsp2_scale, concentration=gsp2_concentration)

    if confirm_order_form_generation(gsp1_list):
        gsp1_order_form_path = os.path.join(output_directory, f"AD{pool_id}-1_IDT_Order_form.xlsm")
        print(f"Writing GSP1 order form to: {gsp1_order_form_path}")
        _write_idt_order_form(gsp1_order_form_path, gsp1_list, pool_id, mix_buffer)

    if confirm_order_form_generation(gsp2_list):
        gsp2_order_form_path = os.path.join(output_directory, f"AD{pool_id}-2_IDT_Order_form.xlsm")
        print(f"Writing GSP2 order form to: {gsp2_order_form_path}")
        _write_idt_order_form(gsp2_order_form_path, gsp2_list, pool_id, mix_buffer)
