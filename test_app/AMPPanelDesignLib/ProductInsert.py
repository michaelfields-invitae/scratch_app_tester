import math
import os
from typing import Optional, List, Dict
from docxtpl import DocxTemplate

from templates.ProductInsertTemplateFiles import ProductInsertTemplateFiles


class PCRInfo:
    def __init__(self, pcr_1_temp: int, pcr_1_anneal_time: int, pcr_2_anneal_time: int, pcr_1_cycles: int,
                 pcr_2_cycles: int) -> None:
        self.pcr_1_temp: str = str(pcr_1_temp)
        self.pcr_1_anneal_time: str = str(pcr_1_anneal_time)
        self.pcr_2_anneal_time: str = str(pcr_2_anneal_time)
        self.pcr_1_cycles: str = str(pcr_1_cycles)
        self.pcr_2_cycles: str = str(pcr_2_cycles)


def _get_reads_required_string(reads_required: int) -> str:
    # declaring these variables to avoid typo errors (e.g. incorrect number of zeroes)
    ONEK = 1000
    ONEHUNDREDK = 100 * ONEK
    FIVEHUNDREDK = 5 * ONEHUNDREDK
    ONEMILLION = 2 * FIVEHUNDREDK

    """Calculates recommended reads using
            Invitae's latest rounding rules"""

    # Above 1M round to nearest 500K, below round up to nearest 100K
    round_up = math.ceil(reads_required / ONEHUNDREDK) * ONEHUNDREDK

    if round_up < ONEMILLION:
        return f"{round_up / ONEK:g}K"
    else:
        # note that Invitae wants a round-half-up rounding rather than
        # python's built in round (round-half-to-even)
        # see:
        # https://realpython.com/python-rounding/#pythons-built-in-round-function

        round_nearest = math.floor(reads_required / FIVEHUNDREDK + 0.5) * FIVEHUNDREDK
        return f"{round_nearest / ONEMILLION:g}M"


class BaseProductInsert:
    def __init__(self, panel_name: str, num_gsp2_primers: int, num_reactions: int, num_reads_required: Optional[int],
                 prefix: str, design_id: str, analysis_version: str, month: str, year: str) -> None:
        self.num_gsp2_primers = num_gsp2_primers

        recommended_reads = num_reads_required if num_reads_required is not None else self.recommended_reads
        recommended_reads_str = _get_reads_required_string(recommended_reads)
        self.context = {"panel_name": panel_name,
                        "num_reactions": num_reactions,
                        "prefix": prefix,
                        "design_id": design_id,
                        "recommended_reads": recommended_reads_str,
                        "analysis_version": analysis_version,
                        "pcr_info": self.pcr_info,
                        "reagent_volumes": self.reagent_volumes,
                        "pipelines": self.pipelines,
                        "month": month,
                        "year": year
                        }  # type: Dict[str, str]

    @property
    def pcr_info(self) -> PCRInfo:
        raise NotImplementedError

    @property
    def reagent_volumes(self) -> List[int]:
        raise NotImplementedError

    @property
    def recommended_reads(self) -> int:
        raise NotImplementedError

    @property
    def pipelines(self) -> List[str]:
        raise NotImplementedError

    @property
    def docx_template_path(self) -> str:
        raise NotImplementedError

    @property
    def document_id(self) -> str:
        raise NotImplementedError

    @property
    def assay_name(self) -> str:
        raise NotImplementedError

    @property
    def default_file_name(self) -> str:
        panel_name = self.context['panel_name']
        design_id = self.context['design_id']
        file_name = f"{self.document_id} {self.assay_name} {panel_name} {design_id}.docx"
        return file_name

    def write(self, output_folder: str, file_name: Optional[str] = None) -> None:
        if file_name is None:
            file_name = self.default_file_name

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        output_file_path = os.path.join(output_folder, file_name)
        doc = DocxTemplate(self.docx_template_path)
        doc.render(self.context)
        doc.save(output_file_path)


class FusionPlexTemplate(BaseProductInsert):
    def __init__(self, panel_name: str, num_gsp2_primers: int, num_reactions: int, num_reads_required: Optional[int],
                 prefix: str, design_id: str, analysis_version: str, month: str, year: str) -> None:
        BaseProductInsert.__init__(self, panel_name, num_gsp2_primers, num_reactions, num_reads_required, prefix,
                                   design_id, analysis_version, month, year)

    @property
    def document_id(self) -> str:
        return "PI017.1"

    @property
    def assay_name(self) -> str:
        return "FusionPlex"

    @property
    def docx_template_path(self) -> str:
        return ProductInsertTemplateFiles.fusionplex_template_file

    @property
    def recommended_reads(self) -> int:
        return self.num_gsp2_primers * 3000

    @property
    def pcr_info(self) -> PCRInfo:
        if self.num_gsp2_primers >= 3001:
            return PCRInfo(pcr_1_temp=60, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 2001:
            return PCRInfo(pcr_1_temp=61, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 1001:
            return PCRInfo(pcr_1_temp=62, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 501:
            return PCRInfo(pcr_1_temp=63, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 20:
            return PCRInfo(pcr_1_temp=65, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        else:
            raise Exception("Cannot determine PCR details because number of GSP2 primer count is below the threshold"
                            f" of 20 ({self.num_gsp2_primers})")

    @property
    def pipelines(self) -> List[str]:
        return []

    @property
    def reagent_volumes(self):
        # type: () -> List[int]
        return []


class LiquidPlexTemplate(BaseProductInsert):
    def __init__(self, panel_name: str, num_gsp2_primers: int, num_reactions: int, num_reads_required: Optional[int],
                 prefix: str, design_id: str, analysis_version: str, month: str, year: str, snv_flag: bool,
                 cnv_flag: bool, sv_flag: bool) -> None:
        self.cnv_flag: bool = cnv_flag
        self.snv_flag: bool = snv_flag
        self.sv_flag: bool = sv_flag
        BaseProductInsert.__init__(self, panel_name, num_gsp2_primers, num_reactions, num_reads_required, prefix,
                                   design_id, analysis_version, month, year)

    @property
    def document_id(self) -> str:
        return "PI016.3"

    @property
    def assay_name(self) -> str:
        return "LiquidPlex"

    @property
    def pcr_info(self) -> PCRInfo:
        if self.num_gsp2_primers >= 4000:
            return PCRInfo(pcr_1_temp=60, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 3000:
            return PCRInfo(pcr_1_temp=61, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 2000:
            return PCRInfo(pcr_1_temp=62, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 1000:
            return PCRInfo(pcr_1_temp=63, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 20:
            return PCRInfo(pcr_1_temp=65, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15, pcr_2_cycles=20)
        else:
            raise Exception("Cannot determine PCR details because number of GSP2 primer count is below the threshold"
                            f" of 20 ({self.num_gsp2_primers})")

    @property
    def reagent_volumes(self) -> List[int]:
        if self.num_gsp2_primers >= 8000:
            return [16, 24, 18, 16, 24]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 16, "A"),
            #     ReagentInfo("First PCR", "LiquidPlex Custom Panel GSP1", 24, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 18, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 18, "D"),
            #     ReagentInfo("Second PCR", "LiquidPlex Custom Panel GSP2", 24, "E")
            # ]
        elif self.num_gsp2_primers >= 3000:
            return [24, 16, 26, 24, 16]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 32, "A"),
            #     ReagentInfo("First PCR", "LiquidPlex Custom Panel GSP1", 8, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 34, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 32, "D"),
            #     ReagentInfo("Second PCR", "LiquidPlex Custom Panel GSP2", 8, "E")
            # ]
        elif self.num_gsp2_primers >= 1000:
            return [32, 8, 34, 32, 8]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 32, "A"),
            #     ReagentInfo("First PCR", "LiquidPlex Custom Panel GSP1", 8, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 34, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 32, "D"),
            #     ReagentInfo("Second PCR", "LiquidPlex Custom Panel GSP2", 8, "E")
            # ]
        elif self.num_gsp2_primers >= 20:
            return [36, 4, 38, 36, 4]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 36, "A"),
            #     ReagentInfo("First PCR", "LiquidPlex Custom Panel GSP1", 4, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 38, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 36, "D"),
            #     ReagentInfo("Second PCR", "LiquidPlex Custom Panel GSP2", 4, "E")
            # ]
        else:
            raise Exception("Cannot determine required reagent volumes because GSP2 primer count is below the threshold"
                            f" of 20 ({self.num_gsp2_primers})")

    @property
    def recommended_reads(self) -> int:
        return self.num_gsp2_primers * 15000

    @property
    def pipelines(self) -> List[str]:
        pipelines: List[str] = []
        if self.snv_flag:
            pipelines.append("SNP/InDel")
        if self.cnv_flag:
            pipelines.append("Copy Number Variation")
        if self.sv_flag:
            pipelines.append("Structural Variation")
        return pipelines

    @property
    def docx_template_path(self) -> str:
        return ProductInsertTemplateFiles.liquidplex_template_file


class VariantPlexHGC2Template(BaseProductInsert):
    def __init__(self, panel_name: str, num_gsp2_primers: int, num_reactions: int, num_reads_required: Optional[int],
                 prefix: str, design_id: str, analysis_version: str, month: str, year: str, snv_flag: bool,
                 cnv_flag: bool, sv_flag: bool, is_blood_cancer: bool) -> None:
        self.cnv_flag: bool = cnv_flag
        self.snv_flag: bool = snv_flag
        self.sv_flag: bool = sv_flag
        self.is_blood_cancer: bool = is_blood_cancer
        BaseProductInsert.__init__(self, panel_name, num_gsp2_primers, num_reactions, num_reads_required, prefix,
                                   design_id, analysis_version, month, year)

    @property
    def document_id(self) -> str:
        return "PI042.0"

    @property
    def assay_name(self) -> str:
        return "VariantPlex"

    @property
    def pcr_info(self) -> PCRInfo:
        if self.is_blood_cancer:
            if self.num_gsp2_primers >= 4000:
                return PCRInfo(pcr_1_temp=60, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 3000:
                return PCRInfo(pcr_1_temp=61, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 2000:
                return PCRInfo(pcr_1_temp=62, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 1000:
                return PCRInfo(pcr_1_temp=63, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 20:
                return PCRInfo(pcr_1_temp=65, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            else:
                raise Exception(
                    "Cannot determine PCR details because number of GSP2 primer count is below the threshold"
                    f" of 20 ({self.num_gsp2_primers})")
        else:
            if self.num_gsp2_primers >= 4000:
                return PCRInfo(pcr_1_temp=60, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 3000:
                return PCRInfo(pcr_1_temp=61, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 2000:
                return PCRInfo(pcr_1_temp=62, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 1000:
                return PCRInfo(pcr_1_temp=63, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 20:
                return PCRInfo(pcr_1_temp=65, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            else:
                raise Exception(
                    "Cannot determine PCR details because number of GSP2 primer count is below the threshold"
                    f" of 20 ({self.num_gsp2_primers})")

    @property
    def reagent_volumes(self) -> List[int]:
        if self.num_gsp2_primers >= 8000:
            return [16, 24, 18, 16, 24]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 16, "A"),
            #     ReagentInfo("First PCR", "VariantPlex Custom Panel GSP1", 24, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 18, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 18, "D"),
            #     ReagentInfo("Second PCR", "VariantPlex Custom Panel GSP2", 24, "E")
            # ]
        elif self.num_gsp2_primers >= 3000:
            return [24, 16, 26, 24, 16]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 32, "A"),
            #     ReagentInfo("First PCR", "LiquidPlex Custom Panel GSP1", 8, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 34, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 32, "D"),
            #     ReagentInfo("Second PCR", "LiquidPlex Custom Panel GSP2", 8, "E")
            # ]
        elif self.num_gsp2_primers >= 1000:
            return [32, 8, 34, 32, 8]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 32, "A"),
            #     ReagentInfo("First PCR", "VariantPlex Custom Panel GSP1", 8, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 34, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 32, "D"),
            #     ReagentInfo("Second PCR", "VariantPlex Custom Panel GSP2", 8, "E")
            # ]
        elif self.num_gsp2_primers >= 20:
            return [36, 4, 38, 36, 4]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 36, "A"),
            #     ReagentInfo("First PCR", "VariantPlex Custom Panel GSP1", 4, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 38, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 36, "D"),
            #     ReagentInfo("Second PCR", "VariantPlex Custom Panel GSP2", 4, "E")
            # ]
        else:
            raise Exception("Cannot determine required reagent volumes because GSP2 primer count is below the threshold"
                            f" of 20 ({self.num_gsp2_primers})")

    @property
    def recommended_reads(self) -> int:
        return self.num_gsp2_primers * 3000

    @property
    def pipelines(self) -> List[str]:
        pipelines: List[str] = []
        if self.snv_flag:
            pipelines.append("SNP/InDel")
        if self.cnv_flag:
            pipelines.append("Copy Number Variation")
        if self.sv_flag:
            pipelines.append("Structural Variation")
        return pipelines

    @property
    def docx_template_path(self) -> str:
        return ProductInsertTemplateFiles.variantplex_hgcv2_template_file


class VariantPlexHSHGCTemplate(BaseProductInsert):
    def __init__(self, panel_name: str, num_gsp2_primers: int, num_reactions: int, num_reads_required: Optional[int],
                 prefix: str, design_id: str, analysis_version: str, month: str, year: str, snv_flag: bool,
                 cnv_flag: bool, sv_flag: bool, is_blood_cancer: bool) -> None:
        self.cnv_flag: bool = cnv_flag
        self.snv_flag: bool = snv_flag
        self.sv_flag: bool = sv_flag
        self.is_blood_cancer: bool = is_blood_cancer
        BaseProductInsert.__init__(self, panel_name, num_gsp2_primers, num_reactions, num_reads_required, prefix,
                                   design_id, analysis_version, month, year)

    @property
    def document_id(self) -> str:
        return "PI015.2"

    @property
    def assay_name(self) -> str:
        return "VariantPlex"

    @property
    def pcr_info(self) -> PCRInfo:
        if self.is_blood_cancer:
            if self.num_gsp2_primers >= 4000:
                return PCRInfo(pcr_1_temp=60, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 3000:
                return PCRInfo(pcr_1_temp=61, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 2000:
                return PCRInfo(pcr_1_temp=62, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 1000:
                return PCRInfo(pcr_1_temp=63, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 20:
                return PCRInfo(pcr_1_temp=65, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            else:
                raise Exception(
                    "Cannot determine PCR details because number of GSP2 primer count is below the threshold"
                    f" of 20 ({self.num_gsp2_primers})")
        else:
            if self.num_gsp2_primers >= 4000:
                return PCRInfo(pcr_1_temp=60, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 3000:
                return PCRInfo(pcr_1_temp=61, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 2000:
                return PCRInfo(pcr_1_temp=62, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 1000:
                return PCRInfo(pcr_1_temp=63, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            elif self.num_gsp2_primers >= 20:
                return PCRInfo(pcr_1_temp=65, pcr_1_anneal_time=10, pcr_2_anneal_time=10, pcr_1_cycles=15,
                               pcr_2_cycles=20)
            else:
                raise Exception(
                    "Cannot determine PCR details because number of GSP2 primer count is below the threshold"
                    f" of 20 ({self.num_gsp2_primers})")

    @property
    def reagent_volumes(self) -> List[int]:
        if self.num_gsp2_primers >= 8000:
            return [16, 24, 18, 16, 24]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 16, "A"),
            #     ReagentInfo("First PCR", "VariantPlex Custom Panel GSP1", 24, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 18, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 18, "D"),
            #     ReagentInfo("Second PCR", "VariantPlex Custom Panel GSP2", 24, "E")
            # ]
        elif self.num_gsp2_primers >= 3000:
            return [24, 16, 26, 24, 16]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 32, "A"),
            #     ReagentInfo("First PCR", "LiquidPlex Custom Panel GSP1", 8, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 34, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 32, "D"),
            #     ReagentInfo("Second PCR", "LiquidPlex Custom Panel GSP2", 8, "E")
            # ]
        elif self.num_gsp2_primers >= 1000:
            return [32, 8, 34, 32, 8]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 32, "A"),
            #     ReagentInfo("First PCR", "VariantPlex Custom Panel GSP1", 8, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 34, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 32, "D"),
            #     ReagentInfo("Second PCR", "VariantPlex Custom Panel GSP2", 8, "E")
            # ]
        elif self.num_gsp2_primers >= 20:
            return [36, 4, 38, 36, 4]
            #     ReagentInfo("Ligation Step 2 Elution", "5mM NaOH", 36, "A"),
            #     ReagentInfo("First PCR", "VariantPlex Custom Panel GSP1", 4, "B"),
            #     ReagentInfo("First PCR", "10mM Tris-HCl pH 8.0", 38, "C"),
            #     ReagentInfo("First PCR", "Purified PCR1 eluate", 36, "D"),
            #     ReagentInfo("Second PCR", "VariantPlex Custom Panel GSP2", 4, "E")
            # ]
        else:
            raise Exception("Cannot determine required reagent volumes because GSP2 primer count is below the threshold"
                            f" of 20 ({self.num_gsp2_primers})")

    @property
    def recommended_reads(self) -> int:
        return self.num_gsp2_primers * 3000

    @property
    def pipelines(self) -> List[str]:
        pipelines: List[str] = []
        if self.snv_flag:
            pipelines.append("SNP/InDel")
        if self.cnv_flag:
            pipelines.append("Copy Number Variation")
        if self.sv_flag:
            pipelines.append("Structural Variation")
        return pipelines

    @property
    def docx_template_path(self) -> str:
        return ProductInsertTemplateFiles.variantplex_hshgc_template_file


class VariantPlexStandardTemplate(BaseProductInsert):
    def __init__(self, panel_name: str, num_gsp2_primers: int, num_reactions: int, num_reads_required: Optional[int],
                 prefix: str, design_id: str, analysis_version: str, month: str, year: str, snv_flag: bool,
                 cnv_flag: bool, sv_flag: bool) -> None:
        self.cnv_flag: bool = cnv_flag
        self.snv_flag: bool = snv_flag
        self.sv_flag: bool = sv_flag
        BaseProductInsert.__init__(self, panel_name, num_gsp2_primers, num_reactions, num_reads_required, prefix,
                                   design_id, analysis_version, month, year)

    @property
    def document_id(self) -> str:
        return "PI014.2"

    @property
    def assay_name(self) -> str:
        return "VariantPlex"

    @property
    def pcr_info(self) -> PCRInfo:
        if self.num_gsp2_primers >= 4000:
            return PCRInfo(pcr_1_temp=60, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 3000:
            return PCRInfo(pcr_1_temp=61, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 2000:
            return PCRInfo(pcr_1_temp=62, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 1000:
            return PCRInfo(pcr_1_temp=63, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        elif self.num_gsp2_primers >= 20:
            return PCRInfo(pcr_1_temp=65, pcr_1_anneal_time=5, pcr_2_anneal_time=5, pcr_1_cycles=15, pcr_2_cycles=20)
        else:
            raise Exception("Cannot determine PCR details because number of GSP2 primer count is below the threshold of"
                            f" 20 ({self.num_gsp2_primers})")

    @property
    def reagent_volumes(self) -> List[int]:
        if self.num_gsp2_primers >= 8000:
            return [14, 8, 12, 14, 8, 12]
            #     ReagentInfo("Cleanup after Adapter Ligation Step 10", "Purified DNA", 14),
            #     ReagentInfo("First PCR Step 2", "VariantPlex Custom Panel GSP1", 8),
            #     ReagentInfo("First PCR Step 3", "Purified DNA", 12),
            #     ReagentInfo("Cleanup after First PCR Step 10", "10mM Tris-HCl pH 8.0", 14),
            #     ReagentInfo("Second PCR Step 2", "VariantPlex Custom Panel GSP2", 8),
            #     ReagentInfo("Second PCR Step 3", "Purified DNA", 12)
            # ]
        elif self.num_gsp2_primers >= 2000:
            return [18, 4, 16, 18, 4, 16]
            #     ReagentInfo("Cleanup after Adapter Ligation Step 10", "Purified DNA", 18),
            #     ReagentInfo("First PCR Step 2", "VariantPlex Custom Panel GSP1", 4),
            #     ReagentInfo("First PCR Step 3", "Purified DNA", 16),
            #     ReagentInfo("Cleanup after First PCR Step 10", "10mM Tris-HCl pH 8.0", 18),
            #     ReagentInfo("Second PCR Step 2", "VariantPlex Custom Panel GSP2", 4),
            #     ReagentInfo("Second PCR Step 3", "Purified DNA", 16)
            # ]
        elif self.num_gsp2_primers >= 20:
            return [20, 2, 18, 20, 2, 18]
            #     ReagentInfo("Cleanup after Adapter Ligation Step 10", "Purified DNA", 20),
            #     ReagentInfo("First PCR Step 2", "VariantPlex Custom Panel GSP1", 2),
            #     ReagentInfo("First PCR Step 3", "Purified DNA", 18),
            #     ReagentInfo("Cleanup after First PCR Step 10", "10mM Tris-HCl pH 8.0", 20),
            #     ReagentInfo("Second PCR Step 2", "VariantPlex Custom Panel GSP2", 2),
            #     ReagentInfo("Second PCR Step 3", "Purified DNA", 18)
            # ]
        else:
            raise Exception("Cannot determine required reagent volumes because GSP2 primer count is below the threshold"
                            f" of 20 ({self.num_gsp2_primers})")

    @property
    def recommended_reads(self) -> int:
        return self.num_gsp2_primers * 500

    @property
    def pipelines(self) -> List[str]:
        pipelines: List[str] = []
        if self.snv_flag:
            pipelines.append("SNP/InDel")
        if self.cnv_flag:
            pipelines.append("Copy Number Variation")
        if self.sv_flag:
            pipelines.append("Structural Variation")
        return pipelines

    @property
    def docx_template_path(self) -> str:
        return ProductInsertTemplateFiles.variantplex_standard_template_file
