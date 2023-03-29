from enum import Enum


class SequencingPlatform:
    def __init__(self, formal_name: str, informal_name: str) -> None:
        self.formal_name: str = formal_name
        self.informal_name: str = informal_name


class SequencingPlatformType(Enum):
    ILLUMINA = SequencingPlatform("Illumina®", "Illumina")
    IONTORRENT = SequencingPlatform("Ion Torrent™", "Ion Torrent")


class Workflow:
    def __init__(self, bundle_name: str, formal_name: str, informal_name: str, abbreviation: str, config_name: str) -> None:
        self.bundle_name: str = bundle_name
        self.formal_name: str = formal_name
        self.informal_name: str = informal_name
        self.abbreviation: str = abbreviation
        self.config_name: str = config_name


class WorkflowType(Enum):
    FUSIONPLEX = Workflow(bundle_name="FusionPlex®", formal_name="FusionPlex®", informal_name="FusionPlex", abbreviation="FP", config_name="FusionPlex")
    VARIANTPLEXSTANDARD = Workflow(bundle_name="VariantPlex®", formal_name="VariantPlex®", informal_name="VariantPlex", abbreviation="VP", config_name="VariantPlex Standard")
    VARIANTPLEXHGC2 = Workflow(bundle_name="VariantPlex®-HGC 2.0", formal_name="VariantPlex®", informal_name="VariantPlex", abbreviation="VP", config_name="VariantPlex HGC2.0")
    VARIANTPLEXHS = Workflow(bundle_name="VariantPlex®-HS", formal_name="VariantPlex®", informal_name="VariantPlex", abbreviation="VP", config_name="VariantPlex HS")
    VARIANTPLEXHGC = Workflow(bundle_name="VariantPlex®-HGC", formal_name="VariantPlex®", informal_name="VariantPlex", abbreviation="VP", config_name="VariantPlex HGC")
    LIQUIDPLEX = Workflow(bundle_name="LiquidPlex™", formal_name="LiquidPlex™", informal_name="LiquidPlex", abbreviation="LP", config_name="LiquidPlex")


class DesignType(Enum):
    GENEMODULE = "Gene Module"
    CATALOGPANEL = "Catalog Panel"


class DiseaseType(Enum):
    SOLIDTUMOR = "Solid Tumor"
    SARCOMA = "Sarcoma"
    BLOODCANCERS = "Blood Cancers"
    GERMLINE = "Germline"


class MoleculeType(Enum):
    RNA = "RNA"
    DNA = "DNA"
    CTDNA = "CTDNA"


class GSPType(Enum):
    GSP1 = "gsp1"
    GSP2 = "gsp2"
