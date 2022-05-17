# from os import stat
from django.contrib import auth
from relecov_core.core_config import (
    HEADING_FOR_RECORD_SAMPLES,
    HEADINGS_FOR_ISkyLIMS,
)
import json

from relecov_core.models import (
    Document,
    SampleState,
    SchemaProperties,
    PropertyOptions,
    Schema,
    Sample,
    MetadataIsCompleted,
    User,
)


def fetch_batch_options():
    data = []
    # check schema
    schema_obj = Schema.objects.filter(
        schema_name="RELECOV", schema_default=True
    ).last()
    # classification="Bioinformatics and QC metrics"
    properties_objs = SchemaProperties.objects.filter(
        fill_mode="batch",
        schemaID=schema_obj,
        classification="Bioinformatics and QC metrics",
    )
    # classification="Contributor Acknowledgement"
    """
    properties_objs2 = SchemaProperties.objects.filter(
        fill_mode="batch",
        schemaID=schema_obj,
        classification="Contributor Acknowledgement",
    )
    """
    for properties_obj in properties_objs:
        data_dict = {}
        if properties_obj.has_options():
            data_dict["Options"] = list(
                PropertyOptions.objects.filter(propertyID_id=properties_obj)
                .values_list("enums", flat=True)
                .distinct()
            )
        data_dict["Label"] = properties_obj.get_label()
        data_dict["Property"] = properties_obj.get_property()
        data_dict["Format"] = properties_obj.get_format()

        data.append(data_dict)
    """
    for properties_obj in properties_objs2:
        data_dict = {}
        if properties_obj.has_options():
            data_dict["Options"] = list(
                PropertyOptions.objects.filter(propertyID_id=properties_obj)
                .values_list("enums", flat=True)
                .distinct()
            )
        data_dict["Label"] = properties_obj.get_label()
        data_dict["Property"] = properties_obj.get_property()
        data_dict["Format"] = properties_obj.get_format()

        data.append(data_dict)
    """
    return data


def fetch_sample_options():
    data = []
    schema_obj = Schema.objects.filter(
        schema_name="RELECOV", schema_default=True
    ).last()
    properties_objs = SchemaProperties.objects.filter(
        fill_mode="sample", schemaID=schema_obj
    )
    for properties_obj in properties_objs:
        data_dict = {}
        if properties_obj.has_options():
            data_dict["Options"] = list(
                PropertyOptions.objects.filter(propertyID_id=properties_obj)
                .values_list("enums", flat=True)
                .distinct()
            )
        data_dict["Label"] = properties_obj.get_label()
        data_dict["Property"] = properties_obj.get_property()
        data_dict["Format"] = properties_obj.get_format()
        data.append(data_dict)

    return data


def sample_table_columns_names():
    sample_table_columns_names = []
    for field in Sample._meta.fields:
        sample_table_columns_names.append(field.get_attname_column()[1])

    return sample_table_columns_names


def get_sample_data(row):
    data = {}
    data_sample = {}
    data_ISkyLIMS = {}
    idx = 0
    headings = fetch_sample_options()
    sample_columns_names = sample_table_columns_names()

    # submittin_lab_sequencing_id => not found
    for heading in headings:
        if heading["Property"] in sample_columns_names:
            data_sample[heading["Property"]] = row[idx]
            idx += 1
        if heading["Label"] in HEADINGS_FOR_ISkyLIMS:
            data_ISkyLIMS[heading["Property"]] = row[idx]
            idx += 1

    data["data_sample"] = data_sample
    data["data_ISkyLIMS"] = data_ISkyLIMS

    return data


def create_metadata_form():
    sample_recorded = {}
    sample_recorded["heading"] = [x[0] for x in HEADING_FOR_RECORD_SAMPLES]
    sample_recorded["batch"] = fetch_batch_options()
    sample_recorded["samples"] = fetch_sample_options()

    return sample_recorded


def execute_query(data, request):
    data_sample = data["data_sample"]

    user = User.objects.get(username=request.user.username)

    metadata_file = Document(
        title="title", file_path="file_path", uploadedFile="uploadedFile.xls"
    )
    metadata_file.save()

    state = SampleState(
        state="1",
        display_string="display_string",
        description="description",
    )
    state.save()

    sample = Sample(
        state=state,
        user=user,
        # user=auth.authenticate(username=request.user.username, password=request.user.password,),
        metadata_file=metadata_file,
        collecting_lab_sample_id=data_sample["collecting_lab_sample_id"],
        sequencing_sample_id=data_sample["sequencing_sample_id"],
        biosample_accession_ENA=data_sample["biosample_accession_ENA"],
        virus_name=data_sample["virus_name"],
        gisaid_id=data_sample["gisaid_id"],
        sequencing_date="",
    )
    sample.save()

    metadata_is_completed = MetadataIsCompleted(
        user=request.user.username,
        sample_data=True,
        batch_data=False,
        sampleID_id=Sample.objects.get(id=sample.id),
    )
    metadata_is_completed.save()

    # TODO - query to ISkyLIMS data
    # data_sample["data_ISkyLIMS"]


def get_dropdown_options():
    properties = get_properties_dict()
    options = get_properties_options(properties)
    return options


def get_properties_dict():
    properties = (
        SchemaProperties.objects.filter(fill_mode="batch")
        .values_list("id", "property")
        .distinct()
    )
    properties_dict = dict(properties)

    return properties_dict


def get_properties_options(properties):
    properties_dict = {}
    for property in properties:
        options = (
            PropertyOptions.objects.filter(propertyID_id=property)
            .values_list("enums", flat=True)
            .distinct()
        )
        options_dict = list(options)
        properties_dict[property] = options_dict
    return options_dict


def analyze_input_samples(request):
    sample_recorded = {}
    na_json_data = json.loads(request.POST["table_data"])
    wrong_rows = process_rows_in_json(na_json_data, request)
    if len(wrong_rows) < 1:
        sample_recorded["process"] = "Success"
        sample_recorded["batch"] = fetch_batch_options()

    else:
        sample_recorded["process"] = "Error"
        sample_recorded["wrong_rows"] = wrong_rows
        sample_recorded["sample"] = fetch_sample_options()

    # print(sample_recorded)
    return sample_recorded


def process_rows_in_json(na_json_data, request):
    wrong_rows = []
    complete_rows = []
    process_rows = {}

    for row in na_json_data:
        if row[0] == "":
            continue

        # check if all fields are completed
        for field in range(len(row)):
            if row[field] == "":
                wrong_rows.append(row)
                break

        if "" not in row:
            complete_rows.append(row)

        process_rows["wrong_rows"] = wrong_rows
        process_rows["complete_rows"] = complete_rows
        for complete_row in complete_rows:
            data = get_sample_data(complete_row)
            execute_query(data, request)

    print("wrong_rows: " + str(wrong_rows))
    print("complete_rows: " + str(complete_rows))

    return wrong_rows
