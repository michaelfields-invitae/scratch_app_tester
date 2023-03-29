import os
from datetime import datetime

from AMPPanelDesignLib.CTF import CTF
from AMPPanelDesignLib.Enums import DiseaseType, WorkflowType
from AMPPanelDesignLib.GTF import GTF
from AMPPanelDesignLib.PanelInfo import PanelInfo
from AMPPanelDesignLib.ProductInsert import FusionPlexTemplate, LiquidPlexTemplate, VariantPlexHGC2Template, \
    VariantPlexHSHGCTemplate, VariantPlexStandardTemplate, BaseProductInsert
from GeneratePanelFilesLib.Logger import Logger


def generate_product_insert_step(logger, panel_info, gtf, ctf, output_directory):
    # type: (Logger, PanelInfo, GTF, CTF, str) -> BaseProductInsert
    logger.message("Generating Product Insert file...")
    if gtf is None:
        logger.warning("No GTF file provided, skipping Product Insert generation")
    elif ctf is None:
        logger.warning("No CTF file provided, skipping Product Insert generation")
    elif panel_info is None:
        logger.warning("No Panel Info config file provided, skipping Product Insert generation")
    else:
        month = datetime.now().strftime("%B")
        year = datetime.now().strftime("%Y")
        blood_cancer = panel_info.disease is DiseaseType.BLOODCANCERS
        snv = False
        cnv = False
        sv = False
        for entry in gtf.entries:
            if "SNV" in entry.attributes.function:
                snv = True
            if "CNV" in entry.attributes.function and "CNV_NO_DISPLAY" not in entry.attributes.function:
                cnv = True
            if any(flag in entry.attributes.function for flag in ["DNA_ANOMALY", "INTERNAL_TANDEM_DUPLICATION"]):
                sv = True
            if snv and cnv and sv:
                break

        if panel_info.workflow is WorkflowType.FUSIONPLEX:
            product_insert = FusionPlexTemplate(panel_name=panel_info.panel_name,
                                                num_gsp2_primers=ctf.unique_gsp2_count,
                                                num_reactions=8,
                                                prefix=panel_info.subassembly_prefix,
                                                num_reads_required=panel_info.reads_required,
                                                design_id=panel_info.panel_id,
                                                analysis_version=panel_info.analysis_version, month=month,
                                                year=year)
        elif panel_info.workflow is WorkflowType.LIQUIDPLEX:
            product_insert = LiquidPlexTemplate(panel_name=panel_info.panel_name,
                                                num_gsp2_primers=ctf.unique_gsp2_count,
                                                num_reactions=8,
                                                prefix=panel_info.subassembly_prefix,
                                                num_reads_required=panel_info.reads_required,
                                                design_id=panel_info.panel_id,
                                                analysis_version=panel_info.analysis_version, month=month,
                                                year=year,
                                                snv_flag=snv, cnv_flag=cnv, sv_flag=sv)
        elif panel_info.workflow is WorkflowType.VARIANTPLEXHGC2:
            product_insert = VariantPlexHGC2Template(panel_name=panel_info.panel_name,
                                                     num_gsp2_primers=ctf.unique_gsp2_count,
                                                     num_reactions=8,
                                                     prefix=panel_info.subassembly_prefix,
                                                     num_reads_required=panel_info.reads_required,
                                                     design_id=panel_info.panel_id,
                                                     analysis_version=panel_info.analysis_version, month=month,
                                                     year=year,
                                                     snv_flag=snv, cnv_flag=cnv, sv_flag=sv,
                                                     is_blood_cancer=blood_cancer)
        elif panel_info.workflow in (WorkflowType.VARIANTPLEXHGC, WorkflowType.VARIANTPLEXHS):
            product_insert = VariantPlexHSHGCTemplate(panel_name=panel_info.panel_name,
                                                      num_gsp2_primers=ctf.unique_gsp2_count,
                                                      num_reactions=8,
                                                      prefix=panel_info.subassembly_prefix,
                                                      num_reads_required=panel_info.reads_required,
                                                      design_id=panel_info.panel_id,
                                                      analysis_version=panel_info.analysis_version, month=month,
                                                      year=year,
                                                      snv_flag=snv, cnv_flag=cnv, sv_flag=sv,
                                                      is_blood_cancer=blood_cancer)
        elif panel_info.workflow is WorkflowType.VARIANTPLEXSTANDARD:
            product_insert = VariantPlexStandardTemplate(panel_name=panel_info.panel_name,
                                                         num_gsp2_primers=ctf.unique_gsp2_count,
                                                         num_reactions=8,
                                                         prefix=panel_info.subassembly_prefix,
                                                         num_reads_required=panel_info.reads_required,
                                                         design_id=panel_info.panel_id,
                                                         analysis_version=panel_info.analysis_version, month=month,
                                                         year=year, snv_flag=snv, cnv_flag=cnv,
                                                         sv_flag=sv)
        else:
            raise Exception(f"Unrecognized workflow template type: {panel_info.workflow}.")
        logger.message(f"Using Product Insert template: {product_insert.docx_template_path}")
        logger.message(f"Writing Product Insert to {os.path.join(output_directory, product_insert.default_file_name)}")
        product_insert.write(output_directory)
        panel_info.reads_required = product_insert.recommended_reads
        return product_insert
