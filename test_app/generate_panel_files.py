import argparse
import os
from typing import Optional, Set

from AMPPanelDesignLib.BED import load_bed
from AMPPanelDesignLib.CTF import load_ctf, load_all_ctfs
from AMPPanelDesignLib.GTF import load_gtf, load_all_gtfs
from AMPPanelDesignLib.InventoryTracking import load_inventory_tracking
from AMPPanelDesignLib.PanelInfo import load_panel_info
from GeneratePanelFilesLib.Logger import Logger
from GeneratePanelFilesLib.WorkflowSteps.BuildBOM import build_bom_step
from GeneratePanelFilesLib.WorkflowSteps.CalculateRawMaterialVolumes import calculate_raw_material_volumes_step
from GeneratePanelFilesLib.WorkflowSteps.CheckRawMaterialInventory import check_raw_material_inventory
from GeneratePanelFilesLib.WorkflowSteps.CleanCTF import clean_ctf_step
from GeneratePanelFilesLib.WorkflowSteps.CleanGTF import clean_gtf_step
from GeneratePanelFilesLib.WorkflowSteps.GenerateProductInsert import generate_product_insert_step

def load_arg_dict(recipe_options):
    print('inside generate_panel_files')
    print(recipe_options)

    args = recipe_options
    ctf_file_path: Optional[str] = args.CTF_filepath
    gtf_file_path: Optional[str] = args.GTF_filepath
    bed_file_path: Optional[str] = args.BED_filepath
    design_repository_folder_path: Optional[str] = args.design_repo_folder
    spike_in_folder_path: Optional[str] = args.spikein_folder
    ignore_ctf_set: Optional[Set[str]] = None  # set(args.ignore_ctf) if args.ignore_ctf is not None else set()
    panel_info_file_path: Optional[str] = args.panel_info_filepath
    inventory_tracking_file_path: Optional[str] = None  # args.inventory_tracking_file
    do_clean_ctf: bool = not args.disable_CTF_cleaning
    do_clean_gtf: bool = not args.disable_GTF_cleaning
    do_generate_product_insert: bool = not args.disable_prod_insert_gen
    do_calculate_volumes: bool = not args.disable_calc_vols_for_raw_mats
    do_generate_dbom: bool = not args.disable_dbom_gen
    do_generate_odoo_bom: bool = not args.disable_odoo_bom_file_gen
    do_generate_label_info: bool = not args.disable_label_info_file_gen
    do_build_bom: bool = do_generate_dbom or do_generate_odoo_bom
    logger: Logger = Logger(is_verbose=args.verbose_logging)
    output_directory: str = args.output_dir

    print('done')

    panel_info = load_panel_info(panel_info_file_path) if panel_info_file_path is not None else None
    ctf = load_ctf(ctf_file_path) if ctf_file_path is not None else None
    gtf = load_gtf(gtf_file_path) if gtf_file_path is not None else None
    bed = load_bed(bed_file_path) if bed_file_path is not None else None
    ctf_repository = load_all_ctfs(design_repository_folder_path,
                                   ignore_ctf_set) if design_repository_folder_path is not None else None
    spike_in_repository = load_all_ctfs(spike_in_folder_path,
                                        ignore_ctf_set) if spike_in_folder_path is not None else None
    gtf_repository = load_all_gtfs(design_repository_folder_path) if design_repository_folder_path is not None else None
    inventory_tracking = load_inventory_tracking(
        inventory_tracking_file_path) if inventory_tracking_file_path is not None else None
    spike_in_ctfs = []
    catalog_gtfs = set()

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    if panel_info is not None and ctf is not None and panel_info.panel_id != ctf.id:
        logger.warning(f"CTF ID ({ctf.id}) and Panel ID found inside {panel_info.file_path} ({panel_info.panel_id}) "
                       f"are not the same. Defaulting to {panel_info.panel_id} for creating filenames.")

    if do_clean_ctf:
        ctf = clean_ctf_step(logger, ctf, output_directory)

    if do_calculate_volumes:
        gsp1_raw_materials, gsp2_raw_materials, spike_in_ctfs = \
            calculate_raw_material_volumes_step(logger, panel_info, ctf, ctf_repository, spike_in_repository,
                                                output_directory)
        # needed for GTF cleaning step
        for raw_material in gsp1_raw_materials:
            if raw_material.is_catalog_panel and raw_material.design_id is not None:
                catalog_gtfs.add(gtf_repository[raw_material.design_id])

        check_raw_material_inventory(logger, panel_info, gsp1_raw_materials, gsp2_raw_materials, inventory_tracking,
                                     output_directory)

    if do_build_bom and (spike_in_ctfs is None or not any(spike_in_ctfs)):
        build_bom_step(logger, panel_info, do_generate_dbom, do_generate_odoo_bom, do_generate_label_info,
                       output_directory)

    if do_clean_gtf:
        gtf = clean_gtf_step(logger, panel_info, gtf, bed, catalog_gtfs, output_directory)

    if do_generate_product_insert and panel_info.supplementary_module_reactions is None:
        product_insert = generate_product_insert_step(logger, panel_info, gtf, ctf, output_directory)

    # panel_info might have been modified by some of the executed steps, so we'll write it to file
    # to see what settings were actually used
    file_name, extension = os.path.splitext(os.path.basename(panel_info.file_path))
    panel_info.file_path = os.path.join(output_directory, f"{file_name}.used{extension}")
    logger.message(f"Writing updated Panel Info file with settings used to {panel_info.file_path}")
    panel_info.write(panel_info.file_path)

    # display a warning if spike-ins were generated
    if any(spike_in_ctfs):
        gene_counts = {}
        for ctf in spike_in_ctfs:
            if not ctf.file_path:
                spike_in_ctf_path = os.path.join(output_directory, f"{panel_info.panel_id}_{ctf.id}.ctf")
                ctf_gene_set = set()
                for entry in ctf.primer_pairs:
                    gene_name = entry.gsp1_name.split("_")[0]
                    if gene_name not in ctf_gene_set:
                        ctf_gene_set.add(gene_name)
                        if gene_name not in gene_counts:
                            gene_counts[gene_name] = []
                        gene_counts[gene_name].append(spike_in_ctf_path)

        for gene in gene_counts:
            if len(gene_counts[gene]) > 1:
                print("\n")
                ctfs_string = "\n".join(gene_counts[gene])
                logger.warning(f"{gene} is split across multiple spike-in CTFs:\n{ctfs_string}")

        print("\n")

        logger.warning(f"Please use a text editor to open {panel_info.file_path} and change the part number and "
                       "ERP description for the spike-in parts under the [GSP1] and/or [GSP2] sections. "
                       "Then rerun this script using the following options to generate the correct BOM files:\n\n"
                       f"-p {panel_info.file_path} -o {output_directory} --no-ctf-clean --no-gtf-clean "
                       f"--no-product-insert --no-volume-calculation {'--verbose' if logger.is_verbose else ''}\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Invitae AMP chemistry panel file generator")
    parser.add_argument("-c", "--ctf-file", required=False, type=str, default=None,
                        help="Path to the CTF file.")
    parser.add_argument("-g", "--gtf-file", required=False, type=str, default=None,
                        help="Path to the GTF file.")
    parser.add_argument("-b", "--bed-file", required=False, type=str, default=None,
                        help="Path to the target coverage BED file.")
    parser.add_argument("-p", "--panel-info-file", required=False, type=str, default=None,
                        help="Path to the panel configuration file.")
    parser.add_argument("-r", "--design-repository-folder", required=False, type=str, default=None,
                        help="Path to the folder containing CTF and GTF files for all inventoried designs.")
    parser.add_argument("-s", "--spike-in-folder", required=False, type=str, default=None,
                        help="Path to the folder containing CTF files for all inventoried designs.")
    parser.add_argument("-i", "--ignore-ctf", action="append", required=False, type=str, default=None,
                        help="Path to a CTF file that will be ignored during raw material volume calculation. "
                             "Option can be used multiple times to ignore multiple CTFs.")
    parser.add_argument("-t", "--inventory-tracking-file", required=False, type=str, default=None,
                        help="Path to the GLI inventory tracking file.")
    parser.add_argument("-o", "--output-dir", required=True, type=str,
                        help="Output directory path. Will create one sub-directory per panel configuration file.")
    parser.add_argument("--no-ctf-clean", action='store_true',
                        help="OPTIONAL: Disables CTF cleaning.")
    parser.add_argument("--no-gtf-clean", action='store_true',
                        help="OPTIONAL: Disables GTF cleaning.")
    parser.add_argument("--no-product-insert", action='store_true',
                        help="OPTIONAL: Disables product insert generation.")
    parser.add_argument("--no-volume-calculation", action='store_true',
                        help="OPTIONAL: Disables calculating volumes for raw materials.")
    parser.add_argument("--no-dbom", action='store_true',
                        help="OPTIONAL: Disables dBOM XML file generation.")
    parser.add_argument("--no-odoo-bom", action='store_true',
                        help="OPTIONAL: Disables Odoo BOM file generation.")
    parser.add_argument("--no-label-info", action='store_true',
                        help="OPTIONAL: Disables label info file generation.")
    parser.add_argument("--verbose", action='store_true',
                        help="OPTIONAL: Enables verbose activity logging to stdout.")

    args = parser.parse_args()
    ctf_file_path: Optional[str] = args.ctf_file
    gtf_file_path: Optional[str] = args.gtf_file
    bed_file_path: Optional[str] = args.bed_file
    design_repository_folder_path: Optional[str] = args.design_repository_folder
    spike_in_folder_path: Optional[str] = args.spike_in_folder
    ignore_ctf_set: Optional[Set[str]] = set(args.ignore_ctf) if args.ignore_ctf is not None else set()
    panel_info_file_path: Optional[str] = args.panel_info_file
    inventory_tracking_file_path: Optional[str] = args.inventory_tracking_file
    do_clean_ctf: bool = not args.no_ctf_clean
    do_clean_gtf: bool = not args.no_gtf_clean
    do_generate_product_insert: bool = not args.no_product_insert
    do_calculate_volumes: bool = not args.no_volume_calculation
    do_generate_dbom: bool = not args.no_dbom
    do_generate_odoo_bom: bool = not args.no_odoo_bom
    do_generate_label_info: bool = not args.no_label_info
    do_build_bom: bool = do_generate_dbom or do_generate_odoo_bom
    logger: Logger = Logger(is_verbose=args.verbose)
    output_directory: str = args.output_dir

    panel_info = load_panel_info(panel_info_file_path) if panel_info_file_path is not None else None
    ctf = load_ctf(ctf_file_path) if ctf_file_path is not None else None
    gtf = load_gtf(gtf_file_path) if gtf_file_path is not None else None
    bed = load_bed(bed_file_path) if bed_file_path is not None else None
    ctf_repository = load_all_ctfs(design_repository_folder_path, ignore_ctf_set) if design_repository_folder_path is not None else None
    spike_in_repository = load_all_ctfs(spike_in_folder_path, ignore_ctf_set) if spike_in_folder_path is not None else None
    gtf_repository = load_all_gtfs(design_repository_folder_path) if design_repository_folder_path is not None else None
    inventory_tracking = load_inventory_tracking(inventory_tracking_file_path) if inventory_tracking_file_path is not None else None
    spike_in_ctfs = []
    catalog_gtfs = set()

    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    if panel_info is not None and ctf is not None and panel_info.panel_id != ctf.id:
        logger.warning(f"CTF ID ({ctf.id}) and Panel ID found inside {panel_info.file_path} ({panel_info.panel_id}) "
                       f"are not the same. Defaulting to {panel_info.panel_id} for creating filenames.")

    if do_clean_ctf:
        ctf = clean_ctf_step(logger, ctf, output_directory)

    if do_calculate_volumes:
        gsp1_raw_materials, gsp2_raw_materials, spike_in_ctfs = \
            calculate_raw_material_volumes_step(logger, panel_info, ctf, ctf_repository, spike_in_repository,
                                                output_directory)
        # needed for GTF cleaning step
        for raw_material in gsp1_raw_materials:
            if raw_material.is_catalog_panel and raw_material.design_id is not None:
                catalog_gtfs.add(gtf_repository[raw_material.design_id])


        check_raw_material_inventory(logger, panel_info, gsp1_raw_materials, gsp2_raw_materials, inventory_tracking,
                                     output_directory)

    if do_build_bom and (spike_in_ctfs is None or not any(spike_in_ctfs)):
        build_bom_step(logger, panel_info, do_generate_dbom, do_generate_odoo_bom, do_generate_label_info, output_directory)

    if do_clean_gtf:
        gtf = clean_gtf_step(logger, panel_info, gtf, bed, catalog_gtfs, output_directory)

    if do_generate_product_insert and panel_info.supplementary_module_reactions is None:
        product_insert = generate_product_insert_step(logger, panel_info, gtf, ctf, output_directory)

    # panel_info might have been modified by some of the executed steps, so we'll write it to file
    # to see what settings were actually used
    file_name, extension = os.path.splitext(os.path.basename(panel_info.file_path))
    panel_info.file_path = os.path.join(output_directory, f"{file_name}.used{extension}")
    logger.message(f"Writing updated Panel Info file with settings used to {panel_info.file_path}")
    panel_info.write(panel_info.file_path)

    # display a warning if spike-ins were generated
    if any(spike_in_ctfs):
        gene_counts = {}
        for ctf in spike_in_ctfs:
            if not ctf.file_path:
                spike_in_ctf_path = os.path.join(output_directory, f"{panel_info.panel_id}_{ctf.id}.ctf")
                ctf_gene_set = set()
                for entry in ctf.primer_pairs:
                    gene_name = entry.gsp1_name.split("_")[0]
                    if gene_name not in ctf_gene_set:
                        ctf_gene_set.add(gene_name)
                        if gene_name not in gene_counts:
                            gene_counts[gene_name] = []
                        gene_counts[gene_name].append(spike_in_ctf_path)

        for gene in gene_counts:
            if len(gene_counts[gene]) > 1:
                print("\n")
                ctfs_string = "\n".join(gene_counts[gene])
                logger.warning(f"{gene} is split across multiple spike-in CTFs:\n{ctfs_string}")

        print("\n")

        logger.warning(f"Please use a text editor to open {panel_info.file_path} and change the part number and "
                       "ERP description for the spike-in parts under the [GSP1] and/or [GSP2] sections. "
                       "Then rerun this script using the following options to generate the correct BOM files:\n\n"
                       f"-p {panel_info.file_path} -o {output_directory} --no-ctf-clean --no-gtf-clean "
                       f"--no-product-insert --no-volume-calculation {'--verbose' if logger.is_verbose else ''}\n")
