# -*- coding: utf-8 -*-
import fauxfactory
import pytest
from selenium.common.exceptions import NoSuchElementException

import cfme.tests.configure.test_access_control as tac
from cfme import test_requirements
from cfme.base.login import BaseLoggedInPage
from cfme.services.catalogs.catalog_items import AddCatalogItemView
from cfme.services.catalogs.catalog_items import AllCatalogItemView
from cfme.services.catalogs.catalog_items import DetailsCatalogItemView
from cfme.services.service_catalogs import ServiceCatalogs
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.blockers import BZ
from cfme.utils.log import logger
from cfme.utils.log_validator import LogValidator
from cfme.utils.update import update


pytestmark = [test_requirements.service, pytest.mark.tier(3), pytest.mark.ignore_stream("upstream")]


@pytest.fixture(scope="function")
def catalog_item(appliance, dialog, catalog):
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name='test_item_{}'.format(fauxfactory.gen_alphanumeric()),
        description="my catalog item", display_in=True,
        catalog=catalog, dialog=dialog
    )
    view = cat_item.create_view(AllCatalogItemView)
    assert view.is_displayed
    view.flash.assert_success_message('Service Catalog Item "{}" was added'.format(
        cat_item.name))
    yield cat_item

    # fixture cleanup
    try:
        cat_item.delete()
    except NoSuchElementException:
        logger.warning('test_catalog_item: catalog_item yield fixture cleanup, catalog item "{}" '
                       'not found'.format(cat_item.name))


@pytest.fixture(scope="function")
def catalog_bundle(appliance, catalog_item):
    """ Create catalog bundle
        Args:
            catalog_item: as resource for bundle creation
    """
    bundle_name = "bundle" + fauxfactory.gen_alphanumeric()
    catalog_bundle = appliance.collections.catalog_bundles.create(
        bundle_name, description="catalog_bundle",
        display_in=True, catalog=catalog_item.catalog,
        dialog=catalog_item.dialog,
        catalog_items=[catalog_item.name])
    yield catalog_bundle

    # fixture cleanup
    try:
        catalog_bundle.delete()
    except NoSuchElementException:
        logger.warning('test_catalog_item: catalog_item yield fixture cleanup, catalog item "{}" '
                       'not found'.format(catalog_bundle.name))


@pytest.fixture(scope="function")
def check_catalog_visibility(user_restricted, tag):
    def _check_catalog_visibility(test_item_object):
        """
            Args:
                test_item_object: object for visibility check
        """
        test_item_object.add_tag(tag)
        with user_restricted:
            assert test_item_object.exists
        test_item_object.remove_tag(tag)
        with user_restricted:
            assert not test_item_object.exists
    return _check_catalog_visibility


def test_catalog_item_crud(appliance, dialog, catalog):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: high
        initialEstimate: 1/8h
        tags: service
    """
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name="test_item_{}".format(fauxfactory.gen_alphanumeric()),
        description="my catalog item",
        display_in=True,
        catalog=catalog,
        dialog=dialog
    )

    # CREATE
    view = cat_item.create_view(AllCatalogItemView)
    assert view.is_displayed
    view.flash.assert_success_message('Service Catalog Item "{}" was added'
                                      .format(cat_item.name))
    assert cat_item.exists

    # EDIT
    with update(cat_item):
        cat_item.description = "my edited description"
    view.flash.assert_success_message('Service Catalog Item "{}" was saved'
                                      .format(cat_item.name))

    view = navigate_to(cat_item, 'Edit')
    view.cancel.click()
    view = cat_item.create_view(DetailsCatalogItemView)
    assert view.wait_displayed()
    view.flash.assert_message('Edit of Service Catalog Item "{}" was cancelled by the user'
                              .format(cat_item.description))
    assert cat_item.description == "my edited description"

    # DELETE
    cat_item.delete()
    view.flash.assert_message("The selected Catalog Item was deleted")
    assert not cat_item.exists


def test_add_button(catalog_item, appliance):
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    button_name = catalog_item.add_button()
    view = appliance.browser.create_view(BaseLoggedInPage)
    if appliance.version.is_in_series('5.8'):
        message = 'Button "{}" was added'.format(button_name)
    else:
        message = 'Custom Button "{}" was added'.format(button_name)
    view.flash.assert_success_message(message)


@test_requirements.tag
def test_edit_tags_catalog_item(catalog_item):
    """
    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        caseimportance: low
        initialEstimate: 1/8h
    """
    tag = catalog_item.add_tag()
    catalog_item.remove_tag(tag)


@pytest.mark.meta(blockers=[BZ(1531512, forced_streams=["5.10", "upstream"])])
def test_catalog_item_duplicate_name(appliance, dialog, catalog):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/8h
        tags: service
    """
    cat_item_name = fauxfactory.gen_alphanumeric()
    cat_item = appliance.collections.catalog_items.create(
        appliance.collections.catalog_items.GENERIC,
        name=cat_item_name,
        description="my catalog item",
        display_in=True,
        catalog=catalog,
        dialog=dialog
    )
    view = cat_item.create_view(AllCatalogItemView, wait='10s')
    view.flash.assert_success_message('Service Catalog Item "{}" was added'.format(cat_item.name))
    with pytest.raises(AssertionError):
        appliance.collections.catalog_items.create(
            appliance.collections.catalog_items.GENERIC,
            name=cat_item_name,
            description="my catalog item",
            display_in=True,
            catalog=catalog,
            dialog=dialog
        )
    view = cat_item.create_view(AddCatalogItemView, wait='10s')
    view.flash.assert_message('Name has already been taken')


def test_permissions_catalog_item_add(appliance, catalog, dialog, request):
    """Test that a catalog can be added only with the right permissions.

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: high
        initialEstimate: 1/8h
        tags: service
    """

    def _create_catalog(appliance):
        cat_item = appliance.collections.catalog_items.create(
            appliance.collections.catalog_items.GENERIC,
            name='test_item_{}'.format(fauxfactory.gen_alphanumeric()),
            description="my catalog item",
            display_in=True,
            catalog=catalog,
            dialog=dialog
        )
        request.addfinalizer(lambda: cat_item.delete())
    test_product_features = [['Everything', 'Services', 'Catalogs Explorer', 'Catalog Items']]
    test_actions = {'Add Catalog Item': _create_catalog}
    tac.single_task_permission_test(appliance, test_product_features, test_actions)


@test_requirements.tag
def test_tagvis_catalog_items(check_catalog_visibility, catalog_item):
    """ Checks catalog item tag visibility for restricted user
    Prerequisites:
        Catalog, tag, role, group and restricted user should be created

    Steps:
        1. As admin add tag to catalog item
        2. Login as restricted user, catalog item is visible for user
        3. As admin remove tag
        4. Login as restricted user, catalog item is not visible for user

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        initialEstimate: 1/8h
    """
    check_catalog_visibility(catalog_item)


@test_requirements.tag
def test_tagvis_catalog_bundle(check_catalog_visibility, catalog_bundle):
    """ Checks catalog bundle tag visibility for restricted user
        Prerequisites:
            Catalog, tag, role, group, catalog item and restricted user should be created

        Steps:
            1. As admin add tag to catalog bundle
            2. Login as restricted user, catalog bundle is visible for user
            3. As admin remove tag
            4. Login as restricted user, catalog bundle is not visible for user

    Polarion:
        assignee: anikifor
        casecomponent: Configuration
        initialEstimate: 1/8h
    """
    check_catalog_visibility(catalog_bundle)


def test_restricted_catalog_items_select_for_catalog_bundle(appliance, request, catalog_item,
                                                            user_restricted, tag, soft_assert):
    """Test catalog item restriction while bundle creation

    Polarion:
        assignee: nansari
        initialEstimate: 1/4h
        casecomponent: Services
        tags: service
    """
    catalog_bundles = appliance.collections.catalog_bundles
    with user_restricted:
        view = navigate_to(catalog_bundles, 'Add')
        available_options = view.resources.select_resource.all_options
        soft_assert(len(available_options) == 1 and available_options[0].text == '<Choose>', (
            'Catalog item list in not empty, but should be'
        ))
    catalog_item.add_tag(tag)
    request.addfinalizer(lambda: catalog_item.remove_tag(tag))
    with user_restricted:
        view = navigate_to(catalog_bundles, 'Add')
        available_options = view.resources.select_resource.all_options
        soft_assert(any(
            option.text == catalog_item.name for option in available_options), (
            'Restricted catalog item is not visible while bundle creation'))


@pytest.mark.manual
@test_requirements.service
@pytest.mark.tier(1)
def test_catalog_all_page_after_deleting_selected_template():
    """
    Polarion:
        assignee: nansari
        initialEstimate: 1/12h
        caseimportance: low
        caseposneg: positive
        testtype: functional
        startsin: 5.10
        casecomponent: Services
        tags: service
        testSteps:
            1. Add provider (VMware or scvmm)
            2. Create catalog item (Remember template you selected.)
            3. Order Service catalog item
            4. Go to details page of provider and click on templates
            5. Either delete this template while provisioning process in progress or after
               completing process.
            6. Go to service > catalogs > service catalogs or catalog items
            7. Click on catalog item you created or ordered
    Bugzilla:
        1652858
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(3)
def test_rbac_assigning_multiple_tags_from_same_category_to_catalog_item():
    """ RBAC : Assigning multiple tags from same category to catalog Item
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.5
        tags: service
    Bugzilla:
        1339382
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_change_provider_template_in_catalog_item():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/8h
        startsin: 5.5
        tags: service
        testSteps:
            1. Create a catalog item and select template for a provider in catalog tab
            2. Select datastore etc in environment tab
            3. In catalog tab change template from one provider to another
        expectedResults:
            3. Validation message should be shown
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(2)
def test_able_to_add_long_description_for_playbook_catalog_items():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.9
        tags: service
    """
    pass


@pytest.mark.manual
@pytest.mark.tier(1)
def test_service_reconfigure_in_distributed_environment():
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        testtype: functional
        initialEstimate: 1/4h
        startsin: 5.10
        tags: service
        testSteps:
            1. Create master and child appliance.
            2. raise provisioning request in master and reconfigure in child.
    """
    pass


@pytest.mark.meta(automates=[1678149])
@pytest.mark.ignore_stream("5.10")
@pytest.mark.tier(2)
def test_copy_catalog_item(request, generic_catalog_item):
    """
    Bugzilla:
        1678149

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        startsin: 5.11
        testSteps:
            1. Create catalog
            2. Create catalog item
            3. Make a copy of catalog item
        expectedResults:
            1.
            2.
            3. Able to copy catalog item
    """
    # copy catalog item
    new_cat_item = generic_catalog_item.copy()
    request.addfinalizer(new_cat_item.delete_if_exists)

    # check for catalog item
    assert new_cat_item.exists


@pytest.mark.meta(coverage=[1678123])
@pytest.mark.manual
@pytest.mark.tier(2)
def test_service_select_tenants():
    """
    Bugzilla:
        1678123
    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        startsin: 5.11
        testSteps:
            1. Create catalog
            2. Create catalog item with tenants
            3. login with tenant and check the services
        expectedResults:
            1.
            2.
            3. Services Should be visible to Tenant
    """
    pass


@test_requirements.service
@pytest.mark.tier(1)
@pytest.mark.meta(blockers=[BZ(1668004)])
def test_service_provisioning_email(request, appliance, catalog_item):
    """
    Polarion:
        assignee: nansari
        casecomponent: Services
        caseposneg: negative
        initialEstimate: 1/4h

    Bugzilla:
        1668004
    """
    result = LogValidator(
        "/var/www/miq/vmdb/log/automation.log", failure_patterns=[".*Error during substitution.*"]
    )
    result.start_monitoring()
    service_catalogs = ServiceCatalogs(appliance, catalog_item.catalog, catalog_item.name)
    service_catalogs.order()
    request_description = ("Provisioning Service [{catalog_item_name}] from [{catalog_item_name}]"
                           .format(catalog_item_name=catalog_item.name))
    provision_request = appliance.collections.requests.instantiate(request_description)
    provision_request.wait_for_request(method='ui')
    request.addfinalizer(provision_request.remove_request)
    assert result.validate(wait="60s")


@pytest.mark.meta(coverage=[1746344])
@pytest.mark.manual
@pytest.mark.tier(2)
def test_assigned_unassigned_catalog_items():
    """
    Bugzilla:
        1746344

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.10
        testSteps:
            1. Create two or more Catalog items
            2. Go to Services->Catalogs->Catalogs
            3. Choose Configuration->Add a new Catalog
            4. Select several items in unassigned catalog items list using shift+arrows on keyboard
            5. Click "Move selected items right" button
        expectedResults:
            1.
            2.
            3.
            4.
            5. Selected items should be moved
    """
    pass


@pytest.mark.meta(coverage=[1744459])
@pytest.mark.manual
@pytest.mark.tier(2)
def test_reorder_buttons_in_catalog_items():
    """
    Bugzilla:
        1744459

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.10
        testSteps:
            1. Add a catalog item
            2. Add a few custom buttons from its summary from the toolbar (Configuration)
            3. Select the actions treenode
            4. In the toolbar select Configuration -> Reorder
        expectedResults:
            1.
            2.
            3.
            4. Cancel/save button should be present on the bottom
    """
    pass


@pytest.mark.meta(coverage=[1740899])
@pytest.mark.manual
@pytest.mark.tier(2)
def test_dialog_dropdown_int_required():
    """
    Bugzilla:
        1740899

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/16h
        startsin: 5.10
        testSteps:
            1. Create a dialog dropdown that is required with a value type of integer
            2. Order a catalog item that uses that dialog
            3. Make a selection for the dropdown
        expectedResults:
            1.
            2.
            3. The field should validate successfully
    """
    pass


@pytest.mark.meta(coverage=[1740814])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_change_ansible_tower_job_template():
    """
    Bugzilla:
        1740814

    Polarion:
        assignee: nansari
        casecomponent: Services
        caseimportance: medium
        initialEstimate: 1/16h
        startsin: 5.11
        testSteps:
            1. Add a Ansible Tower provider
            2. Add an Ansible Tower Catalog Item with 'Display in Catalog' Checked
            3. Edit the Catalog item, change the Tower job template
        expectedResults:
            1.
            2.
            3. 'Display in Catalog' remains checked after template change
    """
    pass


@pytest.mark.meta(coverage=[1602072])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_catalog_item_price_currency():
    """
    Bugzilla:
        1602072

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/6h
        startsin: 5.11
        testSteps:
            1. Add a generic item with price and currency
            2. Add an ansible playbook item with price and currency
            3. Add generic item with currency but no price
            4. Add generic item with currency but non-float price
            5. Add ansible playbook item with currency but no price
            6. Add Ansible Playbook item with currency but non-float price
            7. Unset currency in generic
        expectedResults:
            1. Able to add price and currency
            2. Able to add price and currency
            3. Validation should be fail for generic item with currency but no price
            4. Validation should be fail for generic item with currency but non-float price
            5. Validation Should be fail for ansible playbook item with currency but no price
            6. Validation should be fail for ansible playbook item with currency but non-float price
            7. Able to unset currency in generic catalog item
    """
    pass


@pytest.mark.meta(coverage=[1740399])
@pytest.mark.manual
@pytest.mark.ignore_stream('5.10')
@pytest.mark.tier(2)
def test_copy_catalog_item_with_tags():
    """
    Bugzilla:
        1740399

    Polarion:
        assignee: nansari
        casecomponent: Services
        initialEstimate: 1/4h
        startsin: 5.11
        testSteps:
            1. Create catalog
            2. Create catalog item
            3. Assign some tags from Policy > Edit Tags
            4. Make a copy of catalog item
        expectedResults:
            1.
            2.
            3.
            4. Tags to be copied with catalog item
    """
    pass
