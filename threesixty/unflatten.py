import sys
import json
import codecs
from collections import OrderedDict

from flattentool import decimal_default
from flattentool.schema import SchemaParser
from flattentool.input import FORMATS as INPUT_FORMATS
from flattentool.lib import parse_sheet_configuration
from flattentool.xml_output import toxml

def unflatten(input_name, base_json=None, input_format=None, output_name=None,
              root_list_path=None, root_is_list=False, encoding='utf8', timezone_name='UTC',
              root_id=None, schema='', convert_titles=False, cell_source_map=None,
              heading_source_map=None, id_name=None, xml=False,
              vertical_orientation=False,
              metatab_name=None, metatab_only=False, metatab_schema='',
              metatab_vertical_orientation=False,
              xml_schemas=None,
              default_configuration='',
              disable_local_refs=False,
              xml_comment=None,
              truncation_length=3,
              **_):
    """
    Unflatten a flat structure (spreadsheet - csv or xlsx) into a nested structure (JSON).

    Amended version of the function found at: https://github.com/OpenDataServices/flatten-tool/blob/master/flattentool/__init__.py#L139-L276
    Changes in this version:
     - accepts a dict for `metatab_schema` and `schema` rather than a filename
     - return dict as response rather than writing to file or printing
     - @TODO: accepts a single CSV file rather than a directory
    """
    if input_format is None:
        raise Exception('You must specify an input format (may autodetect in future')
    elif input_format not in INPUT_FORMATS:
        raise Exception('The requested format is not available')
    if metatab_name and base_json:
        raise Exception('Not allowed to use base_json with metatab')

    if root_is_list:
        base = None
    elif base_json:
        with open(base_json) as fp:
            base = json.load(fp, object_pairs_hook=OrderedDict)
    else:
        base = OrderedDict()


    base_configuration = parse_sheet_configuration(
        [item.strip() for item in default_configuration.split(",")]
    )

    cell_source_map_data = OrderedDict()
    heading_source_map_data = OrderedDict()

    if metatab_name and not root_is_list:
        spreadsheet_input_class = INPUT_FORMATS[input_format]
        spreadsheet_input = spreadsheet_input_class(
            input_name=input_name,
            timezone_name=timezone_name,
            root_list_path='meta',
            include_sheets=[metatab_name],
            convert_titles=convert_titles,
            vertical_orientation=metatab_vertical_orientation,
            id_name=id_name,
            xml=xml,
            use_configuration=False
        )
        if metatab_schema:
            if isinstance(metatab_schema, str):
                parser = SchemaParser(schema_filename=metatab_schema, disable_local_refs=disable_local_refs)
            else:
                parser = SchemaParser(root_schema_dict=metatab_schema, disable_local_refs=disable_local_refs)
            parser.parse()
            spreadsheet_input.parser = parser
        spreadsheet_input.encoding = encoding
        spreadsheet_input.read_sheets()
        result, cell_source_map_data_meta, heading_source_map_data_meta = spreadsheet_input.fancy_unflatten(
            with_cell_source_map=cell_source_map,
            with_heading_source_map=heading_source_map,
        )
        for key, value in (cell_source_map_data_meta or {}).items():
            ## strip off meta/0/ from start of source map as actually data is at top level
            cell_source_map_data[key[7:]] = value
        for key, value in (heading_source_map_data_meta or {}).items():
            ## strip off meta/ from start of source map as actually data is at top level
            heading_source_map_data[key[5:]] = value

        # update individual keys from base configuration
        base_configuration.update(spreadsheet_input.sheet_configuration.get(metatab_name, {}))

        if result:
            base.update(result[0])

    if root_list_path is None:
        root_list_path = base_configuration.get('RootListPath', 'main')
    if id_name is None:
        id_name = base_configuration.get('IDName', 'id')

    if not metatab_only or root_is_list:
        spreadsheet_input_class = INPUT_FORMATS[input_format]
        spreadsheet_input = spreadsheet_input_class(
            input_name=input_name,
            timezone_name=timezone_name,
            root_list_path=root_list_path,
            root_is_list=root_is_list,
            root_id=root_id,
            convert_titles=convert_titles,
            exclude_sheets=[metatab_name],
            vertical_orientation=vertical_orientation,
            id_name=id_name,
            xml=xml,
            base_configuration=base_configuration
        )
        if schema:
            if isinstance(schema, str):
                parser = SchemaParser(schema_filename=schema, rollup=True, root_id=root_id,
                                    disable_local_refs=disable_local_refs, truncation_length=truncation_length)
            else:
                parser = SchemaParser(root_schema_dict=schema, rollup=True, root_id=root_id,
                                    disable_local_refs=disable_local_refs, truncation_length=truncation_length)
            parser.parse()
            spreadsheet_input.parser = parser
        spreadsheet_input.encoding = encoding
        spreadsheet_input.read_sheets()
        result, cell_source_map_data_main, heading_source_map_data_main = spreadsheet_input.fancy_unflatten(
            with_cell_source_map=cell_source_map,
            with_heading_source_map=heading_source_map,
        )
        cell_source_map_data.update(cell_source_map_data_main or {})
        heading_source_map_data.update(heading_source_map_data_main or {})
        if root_is_list:
            base = list(result)
        else:
            base[root_list_path] = list(result)

    if xml:
        xml_root_tag = base_configuration.get('XMLRootTag', 'iati-activities')
        xml_output = toxml(
            base, xml_root_tag, xml_schemas=xml_schemas, root_list_path=root_list_path, xml_comment=xml_comment)
        if output_name is None:
            if sys.version > '3':
                sys.stdout.buffer.write(xml_output)
            else:
                sys.stdout.write(xml_output)
        else:
            with codecs.open(output_name, 'wb') as fp:
                fp.write(xml_output)
    else:
        if output_name is None:
            return base
        else:
            with codecs.open(output_name, 'w', encoding='utf-8') as fp:
                json.dump(base, fp, indent=4, default=decimal_default, ensure_ascii=False)
    if cell_source_map:
        with codecs.open(cell_source_map, 'w', encoding='utf-8') as fp:
            json.dump(cell_source_map_data, fp, indent=4, default=decimal_default, ensure_ascii=False)
    if heading_source_map:
        with codecs.open(heading_source_map, 'w', encoding='utf-8') as fp:
            json.dump(heading_source_map_data, fp, indent=4, default=decimal_default, ensure_ascii=False)