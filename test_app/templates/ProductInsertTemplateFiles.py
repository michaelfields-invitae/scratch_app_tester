import os


class ProductInsertTemplateFiles:
    variantplex_standard_template_file: str = os.path.join(os.path.dirname(__file__),
                                                           "PI014.2 Product Insert VariantPlex Standard Custom Template.docx")
    variantplex_hshgc_template_file: str = os.path.join(os.path.dirname(__file__),
                                                        "PI015.2 Product Insert, VariantPlex HS-HGC Custom Template.docx")
    variantplex_hgcv2_template_file: str = os.path.join(os.path.dirname(__file__),
                                                        "PI042.0 Product Insert VariantPlex HGC v2.0 Custom Template.docx")
    liquidplex_template_file: str = os.path.join(os.path.dirname(__file__),
                                                 "PI016.3 Product Insert LiquidPlex Custom Template.docx")
    fusionplex_template_file: str = os.path.join(os.path.dirname(__file__),
                                                 "PI017.1 Product Insert FusionPlex Custom Template.docx")


class IDTOrderFormTemplateFiles:
    idt_order_form_template_file: str = os.path.join(os.path.dirname(__file__),
                                                     "Archer_Bulk_QC_Order_File_CURRENT_14July2021.xlsm")
