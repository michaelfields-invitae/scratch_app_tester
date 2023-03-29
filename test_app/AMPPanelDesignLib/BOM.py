import os
import xml.dom.minidom as md
from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree as ET
from typing import Optional, List


class Component:
    def __init__(self, erp_part_number: str, erp_description: str, syncade_part_number: Optional[str],
                 syncade_description: Optional[str], quantity: Decimal, unit: str) -> None:
        self.erp_part_number: str = erp_part_number
        self.erp_description: str = erp_description
        self.syncade_part_number: Optional[str] = syncade_part_number
        self.syncade_description: Optional[str] = syncade_description
        self.quantity: Decimal = quantity
        self.unit: str = unit
        self.subcomponents: List[Component] = []

    def __str__(self):
        return "\t".join([self.erp_part_number, self.erp_description, str(self.quantity), self.unit])


class RawMaterial(Component):
    def __init__(self, erp_part_number: str, erp_description: str, syncade_part_number: str, syncade_description: str,
                 quantity: Decimal, unit: str, gli_tag: Optional[str] = None) -> None:
        Component.__init__(self, erp_part_number, erp_description, syncade_part_number,
                           syncade_description, quantity, unit)
        self.gli_tag = gli_tag  # type:Optional[str]


class BulkIntermediate(Component):
    def __init__(self, erp_part_number: str, erp_description: str, syncade_part_number: str, syncade_description: str,
                 actual_fill_volume: Decimal, raw_materials: List[RawMaterial]) -> None:
        Component.__init__(self, erp_part_number, erp_description, syncade_part_number, syncade_description,
                           actual_fill_volume, "mL")
        self.raw_materials: List[RawMaterial] = raw_materials

        dx1577_parts = [rm for rm in self.raw_materials if rm.erp_part_number == "DX1577"]
        if any(dx1577_parts):
            dx1577_total_volume = sum(rm.quantity for rm in dx1577_parts)
            dx1577_component = Component("DX1577", "Production GSPs", None, None, dx1577_total_volume, "mL")
            self.subcomponents.append(dx1577_component)
        self.subcomponents.extend([rm for rm in self.raw_materials if rm.erp_part_number != "DX1577"])


class GSPSubAssembly(Component):
    def __init__(self, erp_part_number: str, erp_description: str, syncade_part_number: str, syncade_description: str,
                 actual_fill_volume_ml: Decimal, nominal_fill_volume_ul: Decimal, label_description: str,
                 cap: Component, tube: Component, label: Component, bulk_intermediate: BulkIntermediate) -> None:
        Component.__init__(self, erp_part_number, erp_description, syncade_part_number, syncade_description, Decimal(1),
                           "EA")
        self.label_description: str = label_description
        self.cap: Component = cap
        self.tube: Component = tube
        self.label: Component = label
        self.actual_fill_volume_ml: Decimal = actual_fill_volume_ml
        self.nominal_fill_volume_ul: Decimal = nominal_fill_volume_ul
        self.bulk_intermediate: BulkIntermediate = bulk_intermediate
        self.subcomponents.extend([cap, tube, label, bulk_intermediate])

    def write_dbom(self, output_directory: str, bol_upper_temp_limit: str, bol_lower_temp_limit: str,
                   bos_bulk_product_type: str, bos_aliquot_product: str) -> str:
        def sub_element(parent_element: ET.Element, tag: str, text: str, *attributes: (str, str)) -> ET.Element:
            element = ET.SubElement(parent_element, tag)
            # This is a helper method to make adding new XML nodes a lot easier
            element.text = text
            for attr in attributes:
                element.set(attr[0], attr[1])
            return element

        def val_element(parent_element: ET.Element, tag: str, text: str, validation_name: str, validation_type: str,
                        *additional_attributes: (str, str)) -> ET.Element:
            # This is a helper method to make adding new XML nodes that have the same "Name=" and "Validation="
            # properties a lot easier
            return sub_element(parent_element, tag, text, ("Name", validation_name),
                               ("Validation", validation_type), *additional_attributes)

        def build_component(parent_element: ET.Element, sequence: str, quantity: str, unit: str, weigh_seq: str,
                            charge_seq: str, output_material: str, syncade_part_number: str, syncade_description: str,
                            erp_part_number: str, erp_description: str, gli_tag: Optional[str] = None) -> None:
            ruo_bulk_part = ET.SubElement(parent_element, "Component")
            val_element(ruo_bulk_part, "ID", syncade_part_number, "ID", "Dropdown")
            val_element(ruo_bulk_part, "Sequence", sequence, "Sequence", "Numeric")
            val_element(ruo_bulk_part, "Description", syncade_description, "Description", "String")
            val_element(ruo_bulk_part, "Alias", "", "Alias", "String")
            val_element(ruo_bulk_part, "Quantity", quantity, "Quantity", "Numeric")
            val_element(ruo_bulk_part, "UOM", unit, "UOM", "String")
            val_element(ruo_bulk_part, "ContainerType", "", "Container Type", "String")
            val_element(ruo_bulk_part, "ContainerSize", "", "Container Size", "String")
            val_element(ruo_bulk_part, "ContainerSizeUM", "", "Container Size UM", "String")
            val_element(ruo_bulk_part, "ScalePrecision", ".00000000", "Scale Precision", "Numeric")
            val_element(ruo_bulk_part, "AreaDispensed", "True", "Area Dispensed", "String")
            val_element(ruo_bulk_part, "AllowPotencyAdjustment", "", "Assay", "String")
            val_element(ruo_bulk_part, "AdjustThisExcipient", "", "Dependent", "String")
            val_element(ruo_bulk_part, "AllowAdjustment", "", "Allow Adjustment", "String")
            val_element(ruo_bulk_part, "LowTolerance", ".00000000", "Lo Pct", "Numeric")
            val_element(ruo_bulk_part, "HighTolerance", ".00000000", "Hi Pct", "Numeric")
            val_element(ruo_bulk_part, "WeighSequence", weigh_seq, "Weigh Seq", "Numeric")
            val_element(ruo_bulk_part, "ChargeSequence", charge_seq, "Charge Seq", "Numeric")
            val_element(ruo_bulk_part, "WeighNotes", "", "Weigh Notes", "String")
            val_element(ruo_bulk_part, "ExcipientIngredient", "False", "Excipient Ingredient", "String")
            val_element(ruo_bulk_part, "ActiveIngredient", "False", "Active Ingredient", "String")
            val_element(ruo_bulk_part, "CountByWeight", "False", "Count By Weight", "String")
            val_element(ruo_bulk_part, "WeighByVolume", "False", "Weigh By Volume", "String")
            val_element(ruo_bulk_part, "MinimumNumberOfPieces", "0", "Min Number Pieces", "String")
            val_element(ruo_bulk_part, "OutputMaterial", output_material, "Output Material", "String")
            val_element(ruo_bulk_part, "ScheduleType", "", "Schedule Type", "String")
            val_element(ruo_bulk_part, "ContainerCount", "", "Container Size", "Numeric")
            val_element(ruo_bulk_part, "Scalable", "Yes", "Scalable", "String")
            val_element(ruo_bulk_part, "CountByWeighPieces", "", "Count By Weigh Pieces", "String")
            val_element(ruo_bulk_part, "WeighingMethod", "", "Weighing Method", "String")
            ET.SubElement(ruo_bulk_part, "StorageCondition")
            ruo_bulk_properties = ET.SubElement(ruo_bulk_part, "CustomProperties")
            val_element(ruo_bulk_properties, "Property", erp_part_number, "ERP Part Number", "String")
            val_element(ruo_bulk_properties, "Property", erp_description, "ERP Part Description", "String")
            val_element(ruo_bulk_properties, "Property", gli_tag if gli_tag is not None else "", "GLI Tag", "String")

        dbom = ET.Element("dBOM")
        version = ET.SubElement(ET.SubElement(dbom, "Versions"), "Version")
        sub_element(version, "VersionLabel", "1")
        sub_element(version, "CreationDate", datetime.today().strftime('%Y-%m-%d'))
        sub_element(version, "CreatedBy", "dbom_generator_script.py v1.0")
        bom = ET.SubElement(dbom, "BOM")
        bom_header = ET.SubElement(bom, "BOMHeader")
        val_element(bom_header, "BOMID", f"BOM_{self.erp_part_number}", "Formulation ", "String")
        val_element(bom_header, "Sequence", "99", "Sequence ", "Numeric")
        val_element(bom_header, "Status", "Effective", "Status", "String")
        val_element(bom_header, "MaterialID", self.syncade_part_number, "Material ID", "Dropdown")
        val_element(bom_header, "MaterialDescription", self.syncade_description, "Description", "String")
        val_element(bom_header, "Classification", "", "Classification", "String")
        val_element(bom_header, "Quantity", "1", "Quantity", "Numeric", ("maxlength", "10"))
        val_element(bom_header, "UOM", "ea", "UOM", "Dropdown")
        val_element(bom_header, "UOMDesc", "Eaches", "", "Dropdown")
        recipe = ET.SubElement(bom_header, "Recipe")
        sub_element(recipe, "PrimaryRecipe", "MR_E2E")
        ET.SubElement(recipe, "AlternateRecipe")

        process_segments = ET.SubElement(bom, "ProcessSegments")
        # Bulk BOM
        process_segment_sequence = 0
        sequence_counter = 0
        charge_seq_counter = 0
        if self.bulk_intermediate.raw_materials:
            ruo_bulk_process_segment = ET.SubElement(process_segments, "ProcessSegment")
            val_element(ruo_bulk_process_segment, "Name", "RUO_BULK", "Process Segment", "Dropdown")
            process_segment_sequence += 1
            val_element(ruo_bulk_process_segment, "ProcessSegmentSequence", str(process_segment_sequence), "Sequence",
                        "String")
            val_element(ruo_bulk_process_segment, "Category", "", "Category", "String")
            val_element(ET.SubElement(ruo_bulk_process_segment, "CustomProperties"), "Property", "", "Comments",
                        "String")
            ruo_bulk_components = ET.SubElement(ruo_bulk_process_segment, "Components")
            sequence_counter += 1
            build_component(ruo_bulk_components, str(sequence_counter), "1", "mL", "", "", "Yes",
                            self.bulk_intermediate.syncade_part_number,
                            self.bulk_intermediate.syncade_description,
                            self.bulk_intermediate.erp_part_number,
                            self.bulk_intermediate.erp_description)
            for raw_material in self.bulk_intermediate.raw_materials:
                sequence_counter += 1
                charge_seq_counter += 1
                build_component(ruo_bulk_components, str(sequence_counter), f"{raw_material.quantity:.5f}",
                                raw_material.unit,
                                "1", str(charge_seq_counter), "No",
                                raw_material.syncade_part_number,
                                raw_material.syncade_description,
                                raw_material.erp_part_number,
                                raw_material.erp_description,
                                raw_material.gli_tag)

        # Subassembly BOM
        ruo_subaliquot_process_segment = ET.SubElement(process_segments, "ProcessSegment")
        val_element(ruo_subaliquot_process_segment, "Name", "RUO_SUBALIQUOT", "Process Segment", "Dropdown")
        process_segment_sequence += 1
        val_element(ruo_subaliquot_process_segment, "ProcessSegmentSequence", str(process_segment_sequence), "Sequence",
                    "String")
        val_element(ruo_subaliquot_process_segment, "Category", "", "Category", "String")
        val_element(ET.SubElement(ruo_subaliquot_process_segment, "CustomProperties"), "Property", "",
                    "Comments", "String")
        ruo_subaliquot_components = ET.SubElement(ruo_subaliquot_process_segment, "Components")
        sequence_counter += 1
        build_component(ruo_subaliquot_components, str(sequence_counter), "1", "ea", "", "", "Yes",
                        self.syncade_part_number,
                        self.syncade_description,
                        self.erp_part_number,
                        self.erp_description)
        sequence_counter += 1
        build_component(ruo_subaliquot_components, str(sequence_counter),
                        f"{self.actual_fill_volume_ml:.5f}",
                        "mL", "1", "1", "No",
                        self.bulk_intermediate.syncade_part_number,
                        self.bulk_intermediate.syncade_description,
                        self.bulk_intermediate.erp_part_number,
                        self.bulk_intermediate.erp_description)
        sequence_counter += 1
        build_component(ruo_subaliquot_components, str(sequence_counter), "1", "ea", "1", "2", "No",
                        self.tube.syncade_part_number,
                        self.tube.syncade_description,
                        self.tube.erp_part_number,
                        self.tube.erp_description)
        sequence_counter += 1
        build_component(ruo_subaliquot_components, str(sequence_counter), "1", "ea", "1", "3", "No",
                        self.label.syncade_part_number,
                        self.label.syncade_description,
                        self.label.erp_part_number,
                        self.label.erp_description)
        sequence_counter += 1
        build_component(ruo_subaliquot_components, str(sequence_counter), "1", "ea", "1", "4", "No",
                        self.cap.syncade_part_number,
                        self.cap.syncade_description,
                        self.cap.erp_part_number,
                        self.cap.erp_description)

        bol_labels = ET.SubElement(ET.SubElement(dbom, "BOL"), "Labels")
        bulk_label = ET.SubElement(bol_labels, "Label")
        sub_element(bulk_label, "Alias", "Bulk Label")
        sub_element(bulk_label, "LabelMID", self.bulk_intermediate.erp_part_number)
        sub_element(bulk_label, "LabelTemplate", "BulkLabel")
        sub_element(bulk_label, "LabelQuantity", "1")
        sub_element(bulk_label, "LabelScaling", "No")
        ET.SubElement(bulk_label, "PrinterClass")
        bulk_label_specs = ET.SubElement(bulk_label, "LabelSpecs")
        sub_element(bulk_label_specs, "LabelSpec", self.bulk_intermediate.erp_description, ("Name",
                                                                                            "Description"))
        sub_element(bulk_label_specs, "LabelSpec", f"{bol_upper_temp_limit}°C",
                    ("Name", "Upper Temp Limit"))
        sub_element(bulk_label_specs, "LabelSpec", f"{bol_lower_temp_limit}°C",
                    ("Name", "Lower Temp Limit"))
        sub_element(bulk_label_specs, "LabelSpec", "", ("Name", "Reactions"))
        sub_element(bulk_label_specs, "LabelSpec", self.bulk_intermediate.erp_part_number, ("Name",
                                                                                            "Product Name"))
        sub_element(bulk_label_specs, "LabelSpec", "", ("Name", "Fill Volume"))

        subaliquot_label = ET.SubElement(bol_labels, "Label")
        sub_element(subaliquot_label, "Alias", "Subaliquot Label")
        sub_element(subaliquot_label, "LabelMID", self.erp_part_number)
        sub_element(subaliquot_label, "LabelTemplate", "SubLabel")
        sub_element(subaliquot_label, "LabelQuantity", "1")
        sub_element(subaliquot_label, "LabelScaling", "Yes")
        ET.SubElement(subaliquot_label, "PrinterClass")
        subaliquot_label_specs = ET.SubElement(subaliquot_label, "LabelSpecs")
        sub_element(subaliquot_label_specs, "LabelSpec", self.label_description, ("Name", "Description"))
        sub_element(subaliquot_label_specs, "LabelSpec", f"{bol_upper_temp_limit}°C",
                    ("Name", "Upper Temp Limit"))
        sub_element(subaliquot_label_specs, "LabelSpec", f"{bol_lower_temp_limit}°C",
                    ("Name", "Lower Temp Limit"))
        sub_element(subaliquot_label_specs, "LabelSpec", "8 Reactions", ("Name", "Reactions"))
        sub_element(subaliquot_label_specs, "LabelSpec", self.erp_part_number, ("Name", "Product Name"))
        sub_element(subaliquot_label_specs, "LabelSpec", f"{str(int(self.nominal_fill_volume_ul))} μL",
                    ("Name", "Fill Volume"))

        # Bill of Equipment
        boe_alias = ET.SubElement(ET.SubElement(ET.SubElement(ET.SubElement(dbom, "BOE"), "Equipments"), "Equipment"),
                                  "Alias")
        ET.SubElement(boe_alias, "EquipmentClass")
        ET.SubElement(boe_alias, "EquipmentID")

        # Bill of Documents
        bod_document = ET.SubElement(ET.SubElement(ET.SubElement(dbom, "BOD"), "Documents"), "Document")
        ET.SubElement(bod_document, "Alias")
        ET.SubElement(bod_document, "DocumentDescription")
        ET.SubElement(bod_document, "DocumentName")
        ET.SubElement(bod_document, "DCARepository")
        ET.SubElement(bod_document, "DCAFilePath")

        # Bill of Sample Plan
        bos = ET.SubElement(dbom, "BOS")
        bos_parameters = ET.SubElement(bos, "SamplePlan")
        sub_element(bos_parameters, "Path", "No", ("Alias", "Bulk"))
        sub_element(bos_parameters, "Path", "Yes", ("Alias", "Bulk and Aliquot"))
        sub_element(bos_parameters, "Path", "No", ("Alias", "Aliquot"))
        bos_transitions = ET.SubElement(bos, "Transitions")
        sub_element(bos_transitions, "Transition", bos_bulk_product_type, ("Alias", "Bulk Product Type"))
        sub_element(bos_transitions, "Transition", bos_aliquot_product, ("Alias", "Aliquot Product"))

        # Bill of Parameters
        bop_parameters = ET.SubElement(ET.SubElement(dbom, "BOP"), "Parameters")
        sub_element(bop_parameters, "Parameter", "No", ("Alias", "Retain"))
        sub_element(bop_parameters, "Parameter", "No", ("Alias", "QC Sampling"))
        sub_element(bop_parameters, "Parameter", "No", ("Alias", "Concentration Testing"))
        sub_element(bop_parameters, "Parameter", "No", ("Alias", "PH Testing"))
        sub_element(bop_parameters, "Parameter", "No", ("Alias", "Conductivity Testing"))

        tree = ET.ElementTree(dbom)  # type: ET.ElementTree

        # ET.indent(dbom, "\t", 0)
        # we have to do this stupid hack using minidom to pretty-print the XML outputs because ElementTree.indent() only exists in Python 3.9+
        xml_str = ET.tostring(tree.getroot(), encoding="utf-8", method='xml')
        xml_str: str = md.parseString(xml_str).toprettyxml()
        # ElementTree.tostring() doesn't have an xml_declaration=True parameter for some reason
        xml_str = xml_str.replace('<?xml version="1.0" ?>', '<?xml version="1.0" encoding="utf-8"?>', 1)
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        file_name = f"dBOM_{self.erp_part_number}.xml"
        file_path = os.path.join(output_directory, file_name)
        with open(file_path, 'w') as sw:
            sw.write(xml_str)
        return file_path
