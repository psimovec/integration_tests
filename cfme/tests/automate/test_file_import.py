import fauxfactory
import pytest

from cfme import test_requirements
from cfme.automate.dialog_import_export import DialogImportExport
from cfme.fixtures.automate import DatastoreImport
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.conf import cfme_data
from cfme.utils.ftp import FTPClientWrapper
from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update

pytestmark = [test_requirements.automate, pytest.mark.tier(3)]


@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1715396.zip", "BZ_1715396", None)],
    ids=["sample_domain"],
)
def test_domain_import_file(import_datastore, import_data):
    """This test case Verifies that a domain can be imported from file.

    Polarion:
        assignee: ghubale
        initialEstimate: 1/6h
        caseimportance: medium
        startsin: 5.7
        casecomponent: Automate
        tags: automate
        testSteps:
            1. Navigate to Automation > Automate > Import/Export
            2. Upload zip datastore file
            3. Select domain which like to import
        expectedResults:
            1.
            2.
            3. Import should work. Check imported or not.
    """
    assert import_datastore.exists


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1720611])
@pytest.mark.parametrize("upload_file", ["datastore_blank.zip", "dialog_blank.yml"],
                         ids=["datastore", "dialog"])
@pytest.mark.uncollectif(lambda upload_file: upload_file == "dialog_blank.yml" and
                         BZ(1720611, forced_streams=['5.10']).blocks)
def test_upload_blank_file(appliance, upload_file):
    """
    Bugzilla:
        1720611

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: negative
        startsin: 5.10
        casecomponent: Automate
        testSteps:
            1. Create blank zip(test.zip) and yaml(test.yml) file
            2. Navigate to Automation > Automate > Import/Export and upload test.zip file
            3. Navigate to Automation > Automate > Customization > Import/Export and upload test.yml
        expectedResults:
            1.
            2. Error message should be displayed
            3. Error message should be displayed
    """
    # Download datastore file from FTP server
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.datastores)
    file_path = fs.download(upload_file)

    if upload_file == "dialog_blank.yml":
        with LogValidator("/var/www/miq/vmdb/log/production.log",
                          failure_patterns=[".*FATAL.*"]).waiting(timeout=120):

            # Import dialog yml to appliance
            import_export = DialogImportExport(appliance)
            view = navigate_to(import_export, "DialogImportExport")
            view.upload_file.fill(file_path)
            view.upload.click()
            view.flash.assert_message('Error: the uploaded file is blank')
    else:
        # Import datastore file to appliance
        datastore = appliance.collections.automate_import_exports.instantiate(
            import_type="file", file_path=file_path
        )
        view = navigate_to(appliance.collections.automate_import_exports, "All")
        with LogValidator("/var/www/miq/vmdb/log/production.log",
                          failure_patterns=[".*FATAL.*"]).waiting(timeout=120):
            view.import_file.upload_file.fill(datastore.file_path)
            view.import_file.upload.click()
            view.flash.assert_message("Error: import processing failed: domain: *")


@pytest.mark.tier(2)
@pytest.mark.meta(automates=[1753586])
@pytest.mark.customer_scenario
@pytest.mark.parametrize(
    "import_data",
    [
        DatastoreImport("bz_1753586_user.zip", "bz_1753586_user", None),
        DatastoreImport("bz_1753586_user_locked.zip", "bz_1753586_user_locked", None),
        DatastoreImport("bz_1753586_system.zip", "bz_1753586_system", None),
    ],
    ids=["user", "user_locked", "system"],
)
def test_crud_imported_domains(import_data, temp_appliance_preconfig):
    """
    Bugzilla:
        1753586

    Polarion:
        assignee: ghubale
        initialEstimate: 1/8h
        caseposneg: positive
        casecomponent: Automate
    """
    # Download datastore file from FTP server
    fs = FTPClientWrapper(cfme_data.ftpserver.entities.datastores)
    file_path = fs.download(import_data.file_name)

    # Import datastore file to appliance
    datastore = temp_appliance_preconfig.collections.automate_import_exports.instantiate(
        import_type="file", file_path=file_path
    )
    domain = datastore.import_domain_from(import_data.from_domain, import_data.to_domain)
    assert domain.exists
    if import_data.file_name == "bz_1753586_system.zip":
        # Imported domains with source - "system" can not be deleted or updated as those are
        # defaults like ManageIQ and RedHat domains.
        view = navigate_to(domain, "Details")
        assert not view.configuration.is_displayed
    else:
        view = navigate_to(domain.parent, "All")
        with update(domain):
            domain.description = fauxfactory.gen_alpha()
        domain.delete()
        view.flash.assert_message(f'Automate Domain "{domain.description}": Delete successful')


@pytest.fixture
def setup_automate_model(appliance):
    """This fixture creates domain, namespace, klass"""
    # names and display names of the domain, namespace, klass needs to be static to match with newly
    # imported datastore.
    domain = appliance.collections.domains.create(
        name="bz_1440226",
        description=fauxfactory.gen_alpha(),
        enabled=True)

    namespace = domain.namespaces.create(
        name="test_name",
        description=fauxfactory.gen_alpha()
    )

    klass = namespace.classes.create(
        name="test_class",
        display_name="test_class_display",
        description=fauxfactory.gen_alpha()
    )
    yield domain, namespace, klass
    klass.delete_if_exists()
    namespace.delete_if_exists()
    domain.delete_if_exists()


@pytest.mark.meta(automates=[1440226])
@pytest.mark.parametrize(
    "import_data",
    [DatastoreImport("bz_1440226.zip", "bz_1440226", None)],
    ids=["datastore_update"],
)
def test_automate_import_attributes_updated(setup_automate_model, import_datastore, import_data):
    """
    Note: We are not able to export automate model using automation. Hence importing same datastore
    which is already uploaded on FTP. So step 1 and 2 are performed manually and uploaded that
    datastore on FTP.

    Bugzilla:
        1440226

    Polarion:
        assignee: ghubale
        casecomponent: Automate
        caseimportance: low
        initialEstimate: 1/12h
        tags: automate
        testSteps:
            1. Export an Automate model
            2. Change the description in the exported namespace, class yaml file
            3. Import the updated datastore
            4. Check if the description attribute gets updated
    """
    domain, namespace, klass = setup_automate_model
    view = navigate_to(namespace, "Edit")
    assert view.description.read() == "test_name_desc_updated"
    view = navigate_to(klass, "Edit")
    assert view.description.read() == "test_class_desc"
