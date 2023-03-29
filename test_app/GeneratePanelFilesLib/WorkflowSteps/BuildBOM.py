import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, List

from AMPPanelDesignLib.Enums import WorkflowType, SequencingPlatformType
from AMPPanelDesignLib.BOM import Component, RawMaterial, BulkIntermediate, GSPSubAssembly
from AMPPanelDesignLib.PanelInfo import PanelInfo, RawMaterialInfo
from GeneratePanelFilesLib.Logger import Logger

_tube_component = Component(erp_part_number="K0038",
                            erp_description="Tube, 0.5 ml, PP, skirted base, with assembled cap, sterile",
                            syncade_part_number="K0038",
                            syncade_description="Tube, 0.5 ml, PP, skirted base, with assembled cap, sterile",
                            quantity=Decimal(1.0),
                            unit="EA")
_tube_label_component = Component(erp_part_number="K0191",
                                  erp_description=u"Label, Thermal Transfer, 1.5” x 1”, clear",
                                  syncade_part_number="K0191",
                                  syncade_description=u"Label, Thermal Transfer, 1.5” x 1”, clear",
                                  quantity=Decimal(1.0),
                                  unit="EA")
_red_screw_cap = Component(erp_part_number="K0041",
                           erp_description="Screw Cap Red",
                           syncade_part_number="K0041",
                           syncade_description="Screw Cap Red",
                           quantity=Decimal(1.0),
                           unit="EA")
_black_screw_cap = Component(erp_part_number="K0044",
                             erp_description="Screw Cap Black",
                             syncade_part_number="K0044",
                             syncade_description="Screw Cap Black",
                             quantity=Decimal(1.0),
                             unit="EA")
_box = Component(erp_part_number="DX1868",
                 erp_description="Box, Archer, Small, Soft Touch Laminate",
                 syncade_part_number=None,
                 syncade_description=None,
                 quantity=Decimal(1),
                 unit="EA")
_insert = Component(erp_part_number="DX1869",
                    erp_description="Insert, Small Archer Box, 6-hole",
                    syncade_part_number=None,
                    syncade_description=None,
                    quantity=Decimal(1),
                    unit="EA")
_label = Component(erp_part_number="DX0668",
                   erp_description="Label, Inkjet, Matte Poly, 2.0\" x 2.0\", rolls, 3\" core, 8\" OD, no perf, white",
                   syncade_part_number=None,
                   syncade_description=None,
                   quantity=Decimal(1),
                   unit="EA")
_variantplex_preseq_kits = [Component(erp_part_number="SA0597",
                                      erp_description=u"PreSeq® DNA QC Assay Standard",
                                      syncade_part_number=None,
                                      syncade_description=None,
                                      quantity=Decimal(1),
                                      unit="EA"),
                            Component(erp_part_number="SA0598",
                                      erp_description=u"PreSeq® DNA QC Assay 10X primer Mix",
                                      syncade_part_number=None,
                                      syncade_description=None,
                                      quantity=Decimal(1),
                                      unit="EA")]
_preseq_kits = {WorkflowType.FUSIONPLEX: [Component(erp_part_number="SA0126",
                                                    erp_description="10X VCP Primer",
                                                    syncade_part_number=None,
                                                    syncade_description=None,
                                                    quantity=Decimal(1),
                                                    unit="EA")],
                WorkflowType.VARIANTPLEXSTANDARD: _variantplex_preseq_kits,
                WorkflowType.VARIANTPLEXHS: _variantplex_preseq_kits,
                WorkflowType.VARIANTPLEXHGC: _variantplex_preseq_kits,
                WorkflowType.VARIANTPLEXHGC2: _variantplex_preseq_kits,
                WorkflowType.LIQUIDPLEX: []}

_reagent_kits: Dict[WorkflowType, Dict[SequencingPlatformType, Component]] = {
    WorkflowType.FUSIONPLEX: {
        SequencingPlatformType.ILLUMINA: Component("SK0093", u"FusionPlex® Reagents for Illumina® - 8 reactions",
                                                   None, None, Decimal(1), "EA"),
        SequencingPlatformType.IONTORRENT: Component("SK0094", u"FusionPlex® Reagents for Ion Torrent™ - 8 reactions",
                                                     None, None, Decimal(1), "EA")},
    WorkflowType.LIQUIDPLEX: {
        SequencingPlatformType.ILLUMINA: Component("SK0119", u"LiquidPlex® Reagents for Illumina® - 8 reactions",
                                                   None, None, Decimal(1), "EA")},
    WorkflowType.VARIANTPLEXSTANDARD: {
        SequencingPlatformType.ILLUMINA: Component("SK0098", u"VariantPlex® Reagents for Illumina® - 8 reactions", None,
                                                   None, Decimal(1), "EA")
    },
    WorkflowType.VARIANTPLEXHS: {
        SequencingPlatformType.ILLUMINA: Component("SK0117", u"VariantPlex®-HS Reagents for Illumina® - 8 reactions",
                                                   None, None, Decimal(1), "EA")
    },
    WorkflowType.VARIANTPLEXHGC: {
        SequencingPlatformType.ILLUMINA: Component("SK0115", u"VariantPlex®-HGC Reagents for Illumina® - 8 reactions",
                                                   None, None, Decimal(1), "EA")},
    WorkflowType.VARIANTPLEXHGC2: {
        SequencingPlatformType.ILLUMINA: Component("SK0172",
                                                   u"VariantPlex®-HGC 2.0 Reagents for Illumina® - 8 reactions",
                                                   None, None, Decimal(1), "EA")}}


def _build_raw_materials(gsp_raw_materials: List[RawMaterialInfo], workflow_type: WorkflowType,
                         gsp_num: str) -> List[RawMaterial]:
    raw_materials = []
    for rm in gsp_raw_materials:
        if rm.part_number == "DX0612":
            erp_part_number = "DX0612"
            erp_description = "UltraPure DNase/RNase-Free Distilled Water"
            syncade_part_number = "DX0612"
            syncade_description = "UltraPure DNase/RNase-Free Distilled Water"
            gli_tag = None
        elif rm.is_catalog_panel:
            erp_part_number = rm.part_number
            erp_description = ""
            syncade_part_number = rm.part_number
            syncade_description = ""
            gli_tag = None
        elif rm.is_spike_in:
            erp_part_number = rm.part_number
            erp_description = rm.spike_in_erp_description
            syncade_part_number = f"PS_RM_GSP{gsp_num}"
            syncade_description = f"Panel Specific Spike ins GSP{gsp_num} Raw Material"
            gli_tag = None
        else:
            erp_part_number = "DX1577"
            erp_description = "Production GSPs"
            syncade_part_number = f"{workflow_type.value.abbreviation}_RM_GSP{gsp_num}"
            syncade_description = f"{workflow_type.value.informal_name} GSP{gsp_num} Raw Material"
            gli_tag = rm.part_number

        raw_materials.append(RawMaterial(erp_part_number=erp_part_number, erp_description=erp_description,
                                         syncade_part_number=syncade_part_number,
                                         syncade_description=syncade_description, quantity=rm.volume, unit="mL",
                                         gli_tag=gli_tag))
    return raw_materials


def _build_bulk_intermediate(panel_id: str, panel_name: str, bulk_intermediate_prefix: str, workflow_type: WorkflowType,
                             gsp_num: str, actual_fill_volume: Decimal, raw_materials: List[RawMaterial],
                             supplementary_module: bool):
    erp_part_number = f"{bulk_intermediate_prefix}{panel_id}-{gsp_num}"
    erp_description = f"{workflow_type.value.formal_name} {panel_name}{' Supplement ' if supplementary_module else ' '}GSP{gsp_num} - Bulk"
    syncade_part_number = f"{workflow_type.value.abbreviation}_IM_GSP{gsp_num}"
    syncade_description = f"{workflow_type.value.informal_name} GSP{gsp_num} Intermediate"
    return BulkIntermediate(erp_part_number=erp_part_number, erp_description=erp_description,
                            syncade_part_number=syncade_part_number, syncade_description=syncade_description,
                            actual_fill_volume=actual_fill_volume, raw_materials=raw_materials)


def _build_gsp_subassembly(panel_id: str, panel_name: str, subassembly_prefix: str, workflow_type: WorkflowType,
                           reactions: int, actual_fill_volume: Decimal, nominal_fill_volume: Decimal, gsp_num: str,
                           bulk_intermediate: BulkIntermediate, cap: Component,
                           supplementary_module: bool) -> GSPSubAssembly:
    erp_part_number = f"{subassembly_prefix}{panel_id}{reactions:02d}{gsp_num}"
    erp_description = f"{workflow_type.value.formal_name} {panel_name}{' Supplement ' if supplementary_module else ' '}GSP{gsp_num} - {reactions} reactions"
    syncade_part_number = f"{workflow_type.value.abbreviation}_FG_GSP{gsp_num}"
    syncade_description = f"{workflow_type.value.informal_name} GSP{gsp_num} Finished Good"
    label_description = f"{workflow_type.value.formal_name} {panel_name}"
    return GSPSubAssembly(erp_part_number=erp_part_number, erp_description=erp_description,
                          syncade_part_number=syncade_part_number, syncade_description=syncade_description,
                          actual_fill_volume_ml=actual_fill_volume, nominal_fill_volume_ul=nominal_fill_volume,
                          label_description=label_description, cap=cap, tube=_tube_component,
                          label=_tube_label_component, bulk_intermediate=bulk_intermediate)


def _build_frozen_components_kit(panel_id: str, panel_name: str, frozen_components_kit_prefix: str,
                                 workflow_type: WorkflowType, reactions: int,
                                 gsp1_subassembly: GSPSubAssembly, gsp2_subassembly: GSPSubAssembly) -> Component:
    erp_part_number = f"{frozen_components_kit_prefix}{panel_id}"
    erp_description = f"{workflow_type.value.formal_name} {panel_name} GSP Set - {reactions} reactions"
    preseq_kit = _preseq_kits[workflow_type]
    frozen_components_kit = Component(erp_part_number=erp_part_number, erp_description=erp_description,
                                      syncade_part_number=None, syncade_description=None, quantity=Decimal(1),
                                      unit="EA")
    frozen_components_kit.subcomponents.append(gsp1_subassembly)
    frozen_components_kit.subcomponents.append(gsp2_subassembly)
    frozen_components_kit.subcomponents.extend(preseq_kit)
    frozen_components_kit.subcomponents.append(_box)
    frozen_components_kit.subcomponents.append(_insert)
    frozen_components_kit.subcomponents.append(_label)
    return frozen_components_kit


def _build_movianto_bundle(bundle_id: str, panel_name: str, bundle_prefix: str, workflow_type: WorkflowType,
                           sequencing_platform_type: SequencingPlatformType, reactions: int,
                           frozen_components_kit: Component) -> Component:
    erp_part_number = f"{bundle_prefix}{bundle_id}"
    erp_description = f"{workflow_type.value.bundle_name} {panel_name} for {sequencing_platform_type.value.formal_name} - {reactions} reactions"
    reagent_kit = _reagent_kits[workflow_type][sequencing_platform_type]
    bundle = Component(erp_part_number=erp_part_number, erp_description=erp_description, syncade_part_number=None,
                       syncade_description=None, quantity=Decimal(1), unit="EA")
    bundle.subcomponents.extend([reagent_kit, frozen_components_kit])
    return bundle


def _build_bundle(bundle_id: str, panel_name: str, bundle_prefix: str, workflow_type: WorkflowType,
                  sequencing_platform_type: SequencingPlatformType, reactions: int,
                  gsp1_subassembly: GSPSubAssembly, gsp2_subassembly: GSPSubAssembly) -> Component:
    erp_part_number = f"{bundle_prefix}{bundle_id}"
    erp_description = f"{workflow_type.value.bundle_name} {panel_name} for {sequencing_platform_type.value.formal_name} - {reactions} reactions"
    reagent_kit = _reagent_kits[workflow_type][sequencing_platform_type]
    preseq_kit = _preseq_kits[workflow_type]
    bundle = Component(erp_part_number=erp_part_number, erp_description=erp_description, syncade_part_number=None,
                       syncade_description=None, quantity=Decimal(1), unit="EA")
    bundle.subcomponents.append(reagent_kit)
    bundle.subcomponents.extend(preseq_kit)
    bundle.subcomponents.extend([gsp1_subassembly, gsp2_subassembly])
    return bundle


def _build_supplementary_module(bundle_id: str, panel_name: str, supplementary_module_prefix: str,
                                workflow_type: WorkflowType, reactions: int, gsp1_subassembly: GSPSubAssembly,
                                gsp2_subassembly: GSPSubAssembly) -> Component:
    erp_part_number = f"{supplementary_module_prefix}{bundle_id}"
    erp_description = f"{workflow_type.value.bundle_name} {panel_name} Supplement - {reactions} reactions"
    supplementary_module = Component(erp_part_number=erp_part_number, erp_description=erp_description,
                                     syncade_part_number=None, syncade_description=None, quantity=Decimal(1), unit="EA")
    supplementary_module.subcomponents.extend([gsp1_subassembly, gsp2_subassembly, _box, _insert, _label])
    return supplementary_module


def _write_odoo_bom(bom: Component, panel_info: PanelInfo, file_path: str) -> None:
    def tab(indent_lvl: int, *strings: str) -> str:
        # This is a helper method to make writing a bunch of tab-delimited lines a lot easier
        output = ""
        for i in range(indent_lvl):
            output += "\t"
        output += "\t".join(s if type(s) is str else str(s) for s in strings) + "\n"
        return output

    with open(file_path, "w") as sw:
        sw.write("[Header]\n")
        sw.write(tab(0, "Workflow", panel_info.workflow.value.config_name))
        sw.write(tab(0, "Disease Type", panel_info.disease.value))
        sw.write(tab(0, "Sequencing Platform", panel_info.sequencing_platform.value.informal_name))
        sw.write(tab(0, "Custom Panel Name", panel_info.panel_name))
        sw.write(tab(0, "Custom Panel ID", panel_info.panel_id))
        sw.write(tab(0, "Date Generated", datetime.today().strftime('%Y-%m-%d')))

        # main section
        sw.write("\n")
        sw.write("[Bill of Materials]\n")
        nodes = [(bom, 0)]
        while len(nodes) > 0:
            current_node = nodes.pop()
            component = current_node[0]
            indent_level = current_node[1]
            sw.write(tab(indent_level, str(component)))
            for subcomponent in reversed(component.subcomponents):
                nodes.append((subcomponent, indent_level + 1))


def _write_label_info(gsp1_subassembly: GSPSubAssembly, gsp2_subassembly: GSPSubAssembly,
                      frozen_components_kit: Component, num_reactions: int, file_path: str) -> None:
    with open(file_path, 'w') as sw:
        sw.write("GSP Subassembly Labels\n")
        sw.write("\n")
        sw.write("Label Template:\tTBD\n")
        sw.write(f"Part Number:\t{gsp1_subassembly.erp_part_number}\n")
        sw.write(f"Description:\t{gsp1_subassembly.erp_description}\n")
        sw.write("Storage Conditions:\t-10ºC to -30ºC\n")
        sw.write(f"Fill Volume:\t{int(gsp1_subassembly.nominal_fill_volume_ul)}μL\n")
        sw.write("\n")
        sw.write("Label Template:\tTBD\n")
        sw.write(f"Part Number:\t{gsp2_subassembly.erp_part_number}\n")
        sw.write(f"Description:\t{gsp2_subassembly.erp_description}\n")
        sw.write("Storage Conditions:\t-10ºC to -30ºC\n")
        sw.write(f"Fill Volume:\t{int(gsp2_subassembly.nominal_fill_volume_ul)}μL\n")
        sw.write("\n")
        if frozen_components_kit is not None:
            sw.write("Frozen Components Labels\n")
            sw.write("\n")
            sw.write("Label Template:\tTBD\n")
            sw.write(f"Part Number:\t{frozen_components_kit.erp_part_number}\n")
            sw.write(f"Description:\t{frozen_components_kit.erp_description}\n")
            sw.write("Storage Conditions:\t-10ºC to -30ºC\n")
            sw.write(f"Number of Reactions:\t{num_reactions}\n")


def build_bom_step(logger: Logger, panel_info: PanelInfo, do_generate_dbom: bool, do_generate_odoo_bom: bool,
                   do_generate_label_info: bool, output_directory: str) -> None:
    if panel_info is None:
        logger.warning("No Panel Info config file provided, skipping BOM generation.")
    elif panel_info.actual_fill_volume_ml_gsp1 is None:
        logger.warning("Could not determine GSP1 actual fill volume, skipping BOM generation.")
    elif panel_info.nominal_fill_volume_ul_gsp1 is None:
        logger.warning("Could not determine GSP1 nominal fill volume, skipping BOM generation.")
    elif panel_info.actual_fill_volume_ml_gsp2 is None:
        logger.warning("Could not determine GSP2 actual fill volume, skipping BOM generation.")
    elif panel_info.nominal_fill_volume_ul_gsp2 is None:
        logger.warning("Could not determine GSP2 nominal fill volume, skipping BOM generation.")
    else:
        logger.message("Building BOM...")

        is_supplementary_module = panel_info.supplementary_module_reactions is not None
        num_reactions = panel_info.supplementary_module_reactions or 8

        gsp1_raw_materials = _build_raw_materials(gsp_raw_materials=panel_info.gsp1_raw_materials,
                                                  workflow_type=panel_info.workflow, gsp_num="1")
        gsp2_raw_materials = _build_raw_materials(gsp_raw_materials=panel_info.gsp2_raw_materials,
                                                  workflow_type=panel_info.workflow, gsp_num="2")
        gsp1_bulk_intermediate = _build_bulk_intermediate(panel_id=panel_info.panel_id,
                                                          panel_name=panel_info.panel_name,
                                                          bulk_intermediate_prefix=panel_info.bulk_intermediate_prefix,
                                                          workflow_type=panel_info.workflow,
                                                          gsp_num="1",
                                                          actual_fill_volume=panel_info.actual_fill_volume_ml_gsp1,
                                                          raw_materials=gsp1_raw_materials,
                                                          supplementary_module=is_supplementary_module)
        gsp2_bulk_intermediate = _build_bulk_intermediate(panel_id=panel_info.panel_id,
                                                          panel_name=panel_info.panel_name,
                                                          bulk_intermediate_prefix=panel_info.bulk_intermediate_prefix,
                                                          workflow_type=panel_info.workflow,
                                                          gsp_num="2",
                                                          actual_fill_volume=panel_info.actual_fill_volume_ml_gsp2,
                                                          raw_materials=gsp2_raw_materials,
                                                          supplementary_module=is_supplementary_module)
        gsp1_subassembly = _build_gsp_subassembly(panel_id=panel_info.panel_id,
                                                  panel_name=panel_info.panel_name,
                                                  subassembly_prefix=panel_info.subassembly_prefix,
                                                  workflow_type=panel_info.workflow,
                                                  reactions=num_reactions,
                                                  actual_fill_volume=panel_info.actual_fill_volume_ml_gsp1,
                                                  nominal_fill_volume=panel_info.nominal_fill_volume_ul_gsp1,
                                                  gsp_num="1", bulk_intermediate=gsp1_bulk_intermediate,
                                                  cap=_red_screw_cap, supplementary_module=is_supplementary_module)
        gsp2_subassembly = _build_gsp_subassembly(panel_id=panel_info.panel_id,
                                                  panel_name=panel_info.panel_name,
                                                  subassembly_prefix=panel_info.subassembly_prefix,
                                                  workflow_type=panel_info.workflow,
                                                  reactions=num_reactions,
                                                  actual_fill_volume=panel_info.actual_fill_volume_ml_gsp2,
                                                  nominal_fill_volume=panel_info.nominal_fill_volume_ul_gsp2,
                                                  gsp_num="2", bulk_intermediate=gsp2_bulk_intermediate,
                                                  cap=_black_screw_cap, supplementary_module=is_supplementary_module)

        if do_generate_dbom:
            logger.message("Generating dBOM XML files...")
            gsp1_dbom_path = gsp1_subassembly.write_dbom(output_directory=output_directory,
                                                         bol_upper_temp_limit=panel_info.bol_upper_temp_limit,
                                                         bol_lower_temp_limit=panel_info.bol_lower_temp_limit,
                                                         bos_bulk_product_type=panel_info.bos_bulk_product_type,
                                                         bos_aliquot_product=panel_info.bos_aliquot_product)
            logger.message(f"Writing GSP1 dBOM to {gsp1_dbom_path}")
            gsp2_dbom_path = gsp2_subassembly.write_dbom(output_directory=output_directory,
                                                         bol_upper_temp_limit=panel_info.bol_upper_temp_limit,
                                                         bol_lower_temp_limit=panel_info.bol_lower_temp_limit,
                                                         bos_bulk_product_type=panel_info.bos_bulk_product_type,
                                                         bos_aliquot_product=panel_info.bos_aliquot_product)
            logger.message(f"Writing GSP2 dBOM to {gsp2_dbom_path}")

        frozen_components_kit = None
        if do_generate_odoo_bom:
            logger.message("Generating Odoo BOM file...")
            if is_supplementary_module:
                bom = _build_supplementary_module(bundle_id=panel_info.bundle_id, panel_name=panel_info.panel_name,
                                                  supplementary_module_prefix=panel_info.supplementary_module_prefix,
                                                  workflow_type=panel_info.workflow, reactions=num_reactions,
                                                  gsp1_subassembly=gsp1_subassembly, gsp2_subassembly=gsp2_subassembly)
                if panel_info.movianto_order:
                    frozen_components_kit = bom
            else:
                if panel_info.movianto_order:
                    frozen_components_kit = _build_frozen_components_kit(panel_id=panel_info.panel_id,
                                                                         panel_name=panel_info.panel_name,
                                                                         frozen_components_kit_prefix=panel_info.frozen_components_kit_prefix,
                                                                         workflow_type=panel_info.workflow,
                                                                         reactions=num_reactions,
                                                                         gsp1_subassembly=gsp1_subassembly,
                                                                         gsp2_subassembly=gsp2_subassembly)
                    bom = _build_movianto_bundle(bundle_id=panel_info.bundle_id, panel_name=panel_info.panel_name,
                                                 bundle_prefix=panel_info.bundle_prefix,
                                                 workflow_type=panel_info.workflow,
                                                 sequencing_platform_type=panel_info.sequencing_platform,
                                                 reactions=num_reactions, frozen_components_kit=frozen_components_kit)
                else:
                    bom = _build_bundle(bundle_id=panel_info.bundle_id, panel_name=panel_info.panel_name,
                                        bundle_prefix=panel_info.bundle_prefix, workflow_type=panel_info.workflow,
                                        sequencing_platform_type=panel_info.sequencing_platform,
                                        reactions=num_reactions, gsp1_subassembly=gsp1_subassembly,
                                        gsp2_subassembly=gsp2_subassembly)

            odoo_bom_path = os.path.join(output_directory, f"{panel_info.panel_id}.odoo.txt")
            logger.message(f"Writing Odoo BOM to {odoo_bom_path}")
            _write_odoo_bom(bom, panel_info, odoo_bom_path)

        if do_generate_label_info:
            logger.message("Generating Odoo BOM file...")
            label_info_path = os.path.join(output_directory, f"{panel_info.panel_id}.label_info.txt")
            _write_label_info(gsp1_subassembly, gsp2_subassembly, frozen_components_kit, num_reactions, label_info_path)
