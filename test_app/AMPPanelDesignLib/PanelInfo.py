import os.path
import re
from decimal import Decimal
from typing import List, Optional, Dict, TextIO

from AMPPanelDesignLib.Enums import WorkflowType, SequencingPlatformType, DiseaseType, GSPType
from configs.ConfigurationFiles import ConfigurationFiles


class CatalogPanelSubPart:
    def __init__(self, part_number: str, boost_level_sum: Decimal, gsp_type: Optional[GSPType]) -> None:
        self.part_number: str = part_number
        self.boost_level_sum: Optional[Decimal] = boost_level_sum
        self.gsp_type: GSPType = gsp_type


class CatalogPanelPart:
    def __init__(self, panel_id: str, gsp1_parts: Dict[str, CatalogPanelSubPart],
                 gsp2_parts: Dict[str, CatalogPanelSubPart]) -> None:
        self.panel_id: str = panel_id
        self.gsp1_parts: Dict[str, CatalogPanelSubPart] = gsp1_parts
        self.gsp2_parts: Dict[str, CatalogPanelSubPart] = gsp2_parts

    def __contains__(self, part_number: str) -> bool:
        return part_number in self.gsp1_parts or part_number in self.gsp2_parts


def _load_catalog_panel_ids() -> Dict[str, CatalogPanelPart]:
    catalog_panel_list_file = ConfigurationFiles.catalog_panels_file
    catalog_ids = {}
    with open(catalog_panel_list_file, 'r') as file_reader:
        line = file_reader.readline()
        column_indices = line.strip().split("\t")
        column_indices = {key.casefold(): column_indices.index(key) for key in column_indices}
        line_num = 1
        for line in file_reader:
            line_num += 1
            if not line or line.startswith("#"):
                continue
            line = line.strip().split("\t")
            if len(line) < 3:
                raise Exception(f"Line {line_num} in {catalog_panel_list_file} has fewer than 3 columns")
            panel_id = line[column_indices["catalog panel id"]]
            gsp1_parts = {}
            gsp_part_numbers = line[column_indices["gsp1 part number"]]
            if not gsp_part_numbers:
                raise Exception(f"GSP1 part number missing on line {line_num} of {catalog_panel_list_file}")
            gsp_part_numbers = gsp_part_numbers.strip().split(";")
            for part in gsp_part_numbers:
                part = part.strip().split(",")
                gsp_part_number = part[0].strip()
                if not gsp_part_number:
                    raise Exception(f"GSP1 part number missing on line {line_num} of {catalog_panel_list_file}")
                if len(part) > 1:
                    boost_level_part = Decimal(part[1].strip())
                    if not boost_level_part:
                        raise Exception(f"GSP boost level missing on line {line_num} of {catalog_panel_list_file}")
                else:
                    boost_level_part = None
                gsp1_parts[gsp_part_number] = CatalogPanelSubPart(part_number=gsp_part_number,
                                                                  boost_level_sum=boost_level_part,
                                                                  gsp_type=GSPType.GSP1)
            gsp2_parts = {}
            gsp_part_numbers = line[column_indices["gsp2 part number"]]
            if not gsp_part_numbers:
                raise Exception(f"GSP2 part number missing on line {line_num} of {catalog_panel_list_file}")
            gsp_part_numbers = gsp_part_numbers.strip().split(";")
            for part in gsp_part_numbers:
                part = part.strip().split(",")
                gsp_part_number = part[0].strip()
                if not gsp_part_number:
                    raise Exception(f"GSP2 part number missing on line {line_num} of {catalog_panel_list_file}")
                if len(part) > 1:
                    boost_level_part = Decimal(part[1].strip())
                    if not boost_level_part:
                        raise Exception(f"GSP2 boost level missing on line {line_num} of {catalog_panel_list_file}")
                else:
                    boost_level_part = None
                gsp2_parts[gsp_part_number] = CatalogPanelSubPart(part_number=gsp_part_number,
                                                                  boost_level_sum=boost_level_part,
                                                                  gsp_type=GSPType.GSP2)

            catalog_ids[panel_id] = CatalogPanelPart(panel_id=panel_id, gsp1_parts=gsp1_parts, gsp2_parts=gsp2_parts)
    return catalog_ids


catalog_panel_lookup: Dict[str, CatalogPanelPart] = _load_catalog_panel_ids()


class RawMaterialInfo:
    def __init__(self, part_number: str, design_id: Optional[str], volume: Decimal, is_catalog_panel: bool,
                 spike_in_erp_description: Optional[str] = None) -> None:
        self.part_number: str = part_number
        self.design_id: Optional[str] = design_id
        self.volume: Decimal = volume
        self.is_catalog_panel: bool = is_catalog_panel
        self.spike_in_erp_description: Optional[str] = spike_in_erp_description

    @property
    def is_spike_in(self) -> bool:
        return self.spike_in_erp_description is not None


class PanelInfo:
    def __init__(self, file_path: Optional[str], panel_id: str, panel_name: str, bundle_id: str,
                 workflow_type: WorkflowType, disease_type: DiseaseType,
                 sequencing_platform_type: SequencingPlatformType, analysis_version: str, movianto_order: bool,
                 bulk_intermediate_prefix: str, subassembly_prefix: str, frozen_components_kit_prefix: str,
                 bundle_prefix: str, bol_upper_temp_limit: str, bol_lower_temp_limit: str, bos_bulk_product_type: str,
                 bos_aliquot_product: str, reads_required: Optional[int], max_target_roi_distance: int,
                 gtf_roi_target_buffer: Optional[int], bulk_manufacturing_volume_ml: Decimal,
                 supplementary_module_reactions: Optional[int], supplementary_module_prefix: Optional[str],
                 actual_fill_volume_ml_gsp1: Optional[Decimal], actual_fill_volume_ml_gsp2: Optional[Decimal],
                 nominal_fill_volume_ul_gsp1: Optional[Decimal], nominal_fill_volume_ul_gsp2: Optional[Decimal],
                 gsp1_raw_materials: List[RawMaterialInfo], gsp2_raw_materials: List[RawMaterialInfo]):
        self.file_path: Optional[str] = file_path
        self.panel_id: str = panel_id
        self.panel_name: str = panel_name
        self.bundle_id: str = bundle_id
        self.workflow: WorkflowType = workflow_type
        self.disease: DiseaseType = disease_type
        self.sequencing_platform: SequencingPlatformType = sequencing_platform_type
        self.analysis_version: str = analysis_version

        # settings
        self.movianto_order: bool = movianto_order
        self.bulk_intermediate_prefix: str = bulk_intermediate_prefix
        self.subassembly_prefix: str = subassembly_prefix
        self.frozen_components_kit_prefix: str = frozen_components_kit_prefix
        self.bundle_prefix: str = bundle_prefix
        self.bol_upper_temp_limit: str = bol_upper_temp_limit
        self.bol_lower_temp_limit: str = bol_lower_temp_limit
        self.bos_bulk_product_type: str = bos_bulk_product_type
        self.bos_aliquot_product: str = bos_aliquot_product
        self.reads_required: Optional[int] = reads_required
        self.max_target_roi_distance: int = max_target_roi_distance
        self.gtf_roi_target_buffer: Optional[int] = gtf_roi_target_buffer
        self.bulk_manufacturing_volume_ml: Decimal = bulk_manufacturing_volume_ml

        self.supplementary_module_reactions: Optional[int] = supplementary_module_reactions
        self.supplementary_module_prefix: Optional[str] = supplementary_module_prefix
        self.actual_fill_volume_ml_gsp1: Optional[Decimal] = actual_fill_volume_ml_gsp1
        self.actual_fill_volume_ml_gsp2: Optional[Decimal] = actual_fill_volume_ml_gsp2
        self.nominal_fill_volume_ul_gsp1: Optional[Decimal] = nominal_fill_volume_ul_gsp1
        self.nominal_fill_volume_ul_gsp2: Optional[Decimal] = nominal_fill_volume_ul_gsp2

        self.gsp1_raw_materials: List[RawMaterialInfo] = gsp1_raw_materials
        self.gsp2_raw_materials: List[RawMaterialInfo] = gsp2_raw_materials

    def write(self, file_path):
        def write_line(writer: TextIO, *strings: str) -> None:
            writer.write("\t".join(strings) + "\n")

        def write_raw_material_line(writer: TextIO, raw_material_info: RawMaterialInfo) -> None:
            raw_material_strings = [raw_material_info.part_number, str(raw_material_info.volume)]
            if raw_material_info.is_spike_in:
                raw_material_strings.append(raw_material_info.spike_in_erp_description)
            write_line(writer, *raw_material_strings)

        output_directory = os.path.dirname(file_path)
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)

        with open(file_path, "w") as sw:
            write_line(sw, "[Header]")
            write_line(sw, "Panel ID", self.panel_id)
            write_line(sw, "Panel Name", self.panel_name)
            write_line(sw, "Bundle ID", self.bundle_id)
            write_line(sw, "Workflow", self.workflow.value.config_name)
            write_line(sw, "Disease", self.disease.value)
            write_line(sw, "Sequencing Platform", self.sequencing_platform.value.informal_name)
            write_line(sw, "Analysis Version", self.analysis_version)
            sw.write("\n")

            write_line(sw, "[Settings]")
            write_line(sw, "Movianto Order", str(self.movianto_order))
            write_line(sw, "Bulk Intermediate Prefix", self.bulk_intermediate_prefix)
            write_line(sw, "Subassembly Prefix", self.subassembly_prefix)
            write_line(sw, "Frozen Components Kit Prefix", self.frozen_components_kit_prefix)
            write_line(sw, "Bundle Prefix", self.bundle_prefix)
            if self.bol_upper_temp_limit is not None:
                write_line(sw, "BOL Upper Temp Limit", self.bol_upper_temp_limit)
            if self.bol_lower_temp_limit is not None:
                write_line(sw, "BOL Lower Temp Limit", self.bol_lower_temp_limit)
            if self.bos_bulk_product_type is not None:
                write_line(sw, "BOS Bulk Product Type", self.bos_bulk_product_type)
            if self.bos_aliquot_product is not None:
                write_line(sw, "BOS Aliquot Product", self.bos_aliquot_product)
            if self.reads_required is not None:
                write_line(sw, "Reads Required", str(self.reads_required))
            write_line(sw, "Max Target ROI Distance", str(self.max_target_roi_distance))
            if self.gtf_roi_target_buffer is not None:
                write_line(sw, "GTF ROI Target Buffer", str(self.gtf_roi_target_buffer))
            if self.supplementary_module_reactions is not None:
                write_line(sw, "Supplementary Module Reactions", str(self.supplementary_module_reactions))
            if self.supplementary_module_prefix is not None:
                write_line(sw, "Supplementary Module Prefix", self.supplementary_module_prefix)
            if self.actual_fill_volume_ml_gsp1 is not None:
                write_line(sw, "Actual Fill Volume mL GSP1", f"{self.actual_fill_volume_ml_gsp1:.5f}")
            if self.nominal_fill_volume_ul_gsp2 is not None:
                write_line(sw, "Nominal Fill Volume uL GSP1", f"{self.nominal_fill_volume_ul_gsp1:.5f}")
            if self.actual_fill_volume_ml_gsp2 is not None:
                write_line(sw, "Actual Fill Volume mL GSP2", f"{self.actual_fill_volume_ml_gsp2:.5f}")
            if self.nominal_fill_volume_ul_gsp2 is not None:
                write_line(sw, "Nominal Fill Volume uL GSP2", f"{self.nominal_fill_volume_ul_gsp2:.5f}")
            write_line(sw, "Bulk Manufacturing Volume mL", str(self.bulk_manufacturing_volume_ml))
            sw.write("\n")

            write_line(sw, "[GSP1]")
            for raw_material in self.gsp1_raw_materials:
                write_raw_material_line(sw, raw_material)
            sw.write("\n")
            write_line(sw, "[GSP2]")
            for raw_material in self.gsp2_raw_materials:
                write_raw_material_line(sw, raw_material)


def load_panel_info(file_path: str) -> PanelInfo:
    current_section = ""
    gsp1_raw_materials = []
    gsp2_raw_materials = []
    header = {}
    settings = {}
    with open(file_path, 'r') as file_reader:
        for line in file_reader:
            line = re.split("\t+|,", line.strip())
            if not line:
                continue
            key = line[0].casefold()
            if not key or key.startswith("#"):
                continue
            elif key.startswith("[") and key.endswith("]"):
                current_section = key
            else:
                value = line[1]
                if current_section == "[header]":
                    header[key] = value
                elif current_section == "[settings]":
                    settings[key] = value
                else:
                    if current_section == "[gsp1]":
                        raw_material_list = gsp1_raw_materials
                    elif current_section == "[gsp2]":
                        raw_material_list = gsp2_raw_materials
                    else:
                        raise Exception(f"Unrecognized section in {file_path}: {current_section}")

                    if len(line) < 3:
                        spike_in_erp_description = None
                    else:
                        spike_in_erp_description = line[2]
                    gsp_part_number = line[0]
                    is_catalog_panel = False
                    raw_material_design_id = None
                    for design_id in catalog_panel_lookup:
                        if gsp_part_number in catalog_panel_lookup[design_id]:
                            is_catalog_panel = True
                            raw_material_design_id = design_id
                            break
                    if not is_catalog_panel:
                        raw_material_design_id = gsp_part_number.replace("AD", "", 1).split("-")[0]

                    raw_material_list.append(RawMaterialInfo(part_number=line[0], design_id=raw_material_design_id,
                                                             volume=Decimal(line[1]), is_catalog_panel=is_catalog_panel,
                                                             spike_in_erp_description=spike_in_erp_description))

        workflow = header["workflow"].casefold()
        if workflow == "variantplex standard":
            workflow_type = WorkflowType.VARIANTPLEXSTANDARD
        elif workflow == "variantplex hgc":
            workflow_type = WorkflowType.VARIANTPLEXHGC
        elif workflow == "variantplex hs":
            workflow_type = WorkflowType.VARIANTPLEXHS
        elif workflow == "variantplex hgc2.0":
            workflow_type = WorkflowType.VARIANTPLEXHGC2
        elif workflow == "liquidplex":
            workflow_type = WorkflowType.LIQUIDPLEX
        elif workflow == "fusionplex":
            workflow_type = WorkflowType.FUSIONPLEX
        else:
            raise Exception(f"Unrecognized workflow in {file_path}: {header['workflow']}")

        disease = header["disease"].casefold()
        if disease == "solid tumor":
            disease_type = DiseaseType.SOLIDTUMOR
        elif disease == "blood cancers":
            disease_type = DiseaseType.BLOODCANCERS
        elif disease == "sarcoma":
            disease_type = DiseaseType.SARCOMA
        elif disease == "germline":
            disease_type = DiseaseType.GERMLINE
        else:
            raise Exception(f"Unrecognized disease in {file_path}: {header['disease']}")

        sequencing_platform = header["sequencing platform"].casefold()
        if sequencing_platform == "illumina":
            sequencing_platform_type = SequencingPlatformType.ILLUMINA
        elif sequencing_platform == "ion torrent":
            sequencing_platform_type = SequencingPlatformType.IONTORRENT
        else:
            raise Exception(f"Unrecognized sequencing platform in {file_path}: {header['sequencing platform']}")

    if "movianto order" in settings:
        is_movianto_order = settings["movianto order"].casefold()
        if is_movianto_order == "true" or is_movianto_order == "yes":
            is_movianto_order = True
        elif is_movianto_order == "false" or is_movianto_order == "no":
            is_movianto_order = False
        else:
            raise Exception(f"Invalid value for Movianto Order setting in {file_path}. Must be True or False.")
    else:
        is_movianto_order = False

    # if reads_required is None, it will get auto-calculated by the product insert generation code
    reads_required = settings.get("reads required", None)
    reads_required = int(reads_required) if reads_required is not None else None

    # if gtf_roi_target_buffer is None, it will get auto-calculated by the GTF cleaning code
    gtf_roi_target_buffer = settings.get("gtf roi target buffer", None)
    gtf_roi_target_buffer = int(gtf_roi_target_buffer) if gtf_roi_target_buffer is not None else None

    if "supplementary module reactions" in settings:
        supplementary_module_reactions = int(settings["supplementary module reactions"])
        if supplementary_module_reactions % 8 != 0:
            raise Exception(f"Invalid value for Supplementary Module Reactions in {file_path}: "
                            f"{supplementary_module_reactions}. Must be a multiple of 8")
        if not all([key in settings for key in ["actual fill volume ml gsp1", "actual fill volume ml gsp1",
                                                "nominal fill volume ul gsp1", "nominal fill volume ul gsp2"]]):
            raise Exception(f"The following Settings must be specified in {file_path} when the Supplementary Module "
                            "Reactions setting is used: Actual Fill Volume mL GSP1, Actual Fill Volume GSP2, "
                            "Nominal Fill Volume uL GSP1, Nominal Fill Volume uL GSP2")

    return PanelInfo(file_path=file_path, panel_id=header["panel id"], panel_name=header["panel name"],
                     bundle_id=header["bundle id"], workflow_type=workflow_type, disease_type=disease_type,
                     sequencing_platform_type=sequencing_platform_type, analysis_version=header["analysis version"],
                     movianto_order=is_movianto_order,
                     bulk_intermediate_prefix=settings.get("bulk intermediate prefix", "dGSP"),
                     subassembly_prefix=settings.get("subassembly prefix", "dSA"),
                     frozen_components_kit_prefix=settings.get("frozen components kit prefix", "dSK"),
                     bundle_prefix=settings.get("bundle prefix", "DB"),
                     bol_upper_temp_limit=settings.get("bol upper temp limit", "-10"),
                     bol_lower_temp_limit=settings.get("bol lower temp limit", "-30"),
                     bos_bulk_product_type=settings.get("bos bulk product type", "07"),
                     bos_aliquot_product=settings.get("bos aliquot product", "07"), reads_required=reads_required,
                     max_target_roi_distance=int(settings.get("max target roi distance", 100)),
                     gtf_roi_target_buffer=gtf_roi_target_buffer,
                     bulk_manufacturing_volume_ml=Decimal(settings.get("bulk manufacturing volume ml", 1)),
                     supplementary_module_reactions=int(settings.get("supplementary module reactions", 0)) or None,
                     supplementary_module_prefix=settings.get("supplementary module prefix", "SM"),
                     actual_fill_volume_ml_gsp1=Decimal(settings.get("actual fill volume ml gsp1", 0)) or None,
                     actual_fill_volume_ml_gsp2=Decimal(settings.get("actual fill volume ml gsp2", 0)) or None,
                     nominal_fill_volume_ul_gsp1=Decimal(settings.get("nominal fill volume ul gsp1", 0)) or None,
                     nominal_fill_volume_ul_gsp2=Decimal(settings.get("nominal fill volume ul gsp2", 0)) or None,
                     gsp1_raw_materials=gsp1_raw_materials, gsp2_raw_materials=gsp2_raw_materials)
