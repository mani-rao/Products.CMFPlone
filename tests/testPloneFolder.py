#
# PloneFolder tests
#

import os, sys
if __name__ == '__main__':
    execfile(os.path.join(sys.path[0], 'framework.py'))

from Testing import ZopeTestCase
from Products.CMFPlone.tests import PloneTestCase
from Products.CMFPlone.tests import dummy
from Products.CMFPlone.utils import _createObjectByType
import transaction

from OFS.IOrderSupport import IOrderedContainer

from AccessControl import Unauthorized
from Products.CMFCore.permissions import DeleteObjects

from zExceptions import NotFound
from zExceptions import BadRequest


class TestPloneFolder(PloneTestCase.PloneTestCase):

    def afterSetUp(self):
        # Create a bunch of subfolders
        self.folder.invokeFactory('Folder', id='sub1')
        self.folder.invokeFactory('Folder', id='sub2')
        self.folder.invokeFactory('Folder', id='sub3')

    def testGetObjectPosition(self):
        self.assertEqual(self.folder.getObjectPosition('sub1'), 0)

    def testGetObjectPositionRaisesNotFound(self):
        self.assertRaises(NotFound, self.folder.getObjectPosition, 'foobar')

    def testSortOrder(self):
        self.assertEqual(self.folder.objectIds(), 
            ['sub1', 'sub2', 'sub3'])

    def testEditFolderKeepsPosition(self):
        # Cover http://plone.org/collector/2796
        self.folder.sub2.folder_edit('Foo', 'Description')
        self.assertEqual(self.folder.sub2.Title(), 'Foo')
        # Order should remain the same
        self.assertEqual(self.folder.objectIds(), 
            ['sub1', 'sub2', 'sub3'])

    def testRenameFolderKeepsPosition(self):
        # Cover http://plone.org/collector/2796
        transaction.commit(1) # make rename work
        self.folder.sub2.folder_edit('Foo', 'Description', id='foo')
        self.assertEqual(self.folder.foo.Title(), 'Foo')
        # Order should remain the same
        self.assertEqual(self.folder.objectIds(), 
            ['sub1', 'foo', 'sub3'])

    def testCanViewManagementScreen(self):
        # Make sure the ZMI management screen works
        self.folder.manage_main()

    def testLargePloneFolderIsNotOrdered(self):
        _createObjectByType('Large Plone Folder', self.folder, 'lpf')
        lpf = self.folder.lpf
        self.failIf(IOrderedContainer.isImplementedBy(lpf))


class TestCheckIdAvailable(PloneTestCase.PloneTestCase):
    # PortalFolder.checkIdAvailable() did not properly catch
    # zExceptions.BadRequest. 
    # Fixed in CMFCore.PortalFolder, not Plone.
    
    def afterSetUp(self):
        _createObjectByType('Large Plone Folder', self.folder, 'lpf')
        self.lpf = self.folder.lpf

    def testSetObjectRaisesBadRequest(self):
        # _setObject() should raise zExceptions.BadRequest
        # on duplicate id.
        self.folder._setObject('foo', dummy.Item())
        try:
            self.folder._setObject('foo', dummy.Item())
        except BadRequest:
            pass

    def testCheckIdRaisesBadRequest(self):
        # _checkId() should raise zExceptions.BadRequest
        # on duplicate id.
        self.folder._setObject('foo', dummy.Item())
        try:
            self.folder._checkId('foo')
        except BadRequest:
            pass

    def testCheckIdAvailableCatchesBadRequest(self):
        # checkIdAvailable() should catch zExceptions.BadRequest
        self.folder._setObject('foo', dummy.Item())
        self.failIf(self.folder.checkIdAvailable('foo'))

    def testLPFSetObjectRaisesBadRequest(self):
        # _setObject() should raise zExceptions.BadRequest
        # on duplicate id.
        self.lpf._setObject('foo', dummy.Item())
        try:
            self.lpf._setObject('foo', dummy.Item())
        except BadRequest:
            pass

    def testLPFCheckIdRaisesBadRequest(self):
        # _checkId() should raise zExceptions.BadRequest
        # on duplicate id.
        self.lpf._setObject('foo', dummy.Item())
        try:
            self.lpf._checkId('foo')
        except BadRequest:
            pass

    def testLPFCheckIdAvailableCatchesBadRequest(self):
        # checkIdAvailable() should catch zExceptions.BadRequest
        self.lpf._setObject('foo', dummy.Item())
        self.failIf(self.lpf.checkIdAvailable('foo'))


class TestFolderListing(PloneTestCase.PloneTestCase):
    # Tests for http://plone.org/collector/3512

    def afterSetUp(self):
        self.workflow = self.portal.portal_workflow
        # Create some objects to list
        self.folder.invokeFactory('Folder', id='sub1')
        self.folder.invokeFactory('Folder', id='sub2')
        self.folder.invokeFactory('Document', id='doc1')
        self.folder.invokeFactory('Document', id='doc2')

    def _contentIds(self, folder):
        return [ob.getId() for ob in folder.listFolderContents()]

    def testListFolderContentsOmitsPrivateObjects(self):
        self.workflow.doActionFor(self.folder.doc1, 'hide')
        self.logout()
        self.assertEqual(self._contentIds(self.folder),
                         ['sub1', 'sub2', 'doc2'])

    def testListFolderContentsOmitsPrivateFolders(self):
        self.workflow.doActionFor(self.folder.sub1, 'hide')
        self.logout()
        self.assertEqual(self._contentIds(self.folder),
                         ['sub2', 'doc1', 'doc2'])

    def testBugReport(self):
        # Perform the steps-to-reproduce in the collector issue:

        # 2)
        self.folder.invokeFactory('Folder', id='A')
        self.workflow.doActionFor(self.folder.A, 'publish')

        self.logout()
        self.assertEqual(self._contentIds(self.folder.A), [])

        # 3)
        self.login()
        self.folder.A.invokeFactory('Document', id='B')
        self.folder.A.B.manage_permission('View', ['Manager', 'Reviewer'], acquire=0)

        self.logout()
        self.assertEqual(self._contentIds(self.folder.A), [])

        # 4)
        self.login()
        self.folder.A.invokeFactory('Folder', id='C')
        self.folder.A.C.manage_permission('View', ['Manager', 'Reviewer'], acquire=0)

        # Here comes the reported bug:
        self.logout()
        self.assertEqual(self._contentIds(self.folder.A), ['C']) # <--

        # 4a)
        # BUT: removing 'View' is simply not enough!
        # When using the workflow all is fine:
        self.login()
        self.workflow.doActionFor(self.folder.A.C, 'hide')

        self.logout()
        self.assertEqual(self._contentIds(self.folder.A), [])

        # -> For folders you also have to remove 'Access contents information'
        # -> Never click around in the ZMI security screens, use the workflow!

    def test_folder_contents(self):
        self.folder.sub1.invokeFactory('Document', id='sub1doc1')

        contents = self.folder.sub1.getFolderContents()
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0].getId, 'sub1doc1')

        self.failUnless(self.folder.sub1.folder_contents())

        self.folder.sub1.manage_permission('List folder contents', ['Manager'], acquire=0)

        self.assertRaises(Unauthorized, self.folder.sub1.folder_contents)


class TestManageDelObjects(PloneTestCase.PloneTestCase):
    # manage_delObjects should check 'Delete objects'
    # permission on contained items.

    def afterSetUp(self):
        # Create a bunch of folders
        self.folder.invokeFactory('Folder', id='sub1')
        self.sub1 = self.folder.sub1
        self.sub1.invokeFactory('Folder', id='sub2')
        self.sub2 = self.sub1.sub2

    def testManageDelObjects(self):
        # Should be able to delete sub1
        self.folder.manage_delObjects('sub1')
        self.failIf('sub1' in self.folder.objectIds())

    def testManageDelObjectsIfSub1Denied(self):
        # Should NOT be able to delete sub1 due to permission checks in
        # Archetypes.BaseFolder.manage_delObjects().
        self.sub1.manage_permission(DeleteObjects, ['Manager'], acquire=0)
        self.assertRaises(Unauthorized, self.folder.manage_delObjects, 'sub1')

    def testManageDelObjectsIfSub2Denied(self):
        # We are able to delete sub1 if sub2 is denied
        # -> the check is only 1 level deep!
        self.sub2.manage_permission(DeleteObjects, ['Manager'], acquire=0)
        self.folder.manage_delObjects('sub1')
        self.failIf('sub1' in self.folder.objectIds())


class TestManageDelObjectsInPortal(PloneTestCase.PloneTestCase):

    def afterSetUp(self):
        _createObjectByType('Folder', self.portal, id='sub1')
        self.sub1 = self.portal.sub1

    def testManageDelObjects(self):
        # Should be able to delete sub1
        self.portal.manage_delObjects('sub1')
        self.failIf('sub1' in self.portal.objectIds())

    def testManageDelObjectsIfSub1Denied(self):
        # Should be able to delete sub1 as the portal does not implement
        # additional permission checks.
        self.sub1.manage_permission(DeleteObjects, ['Manager'], acquire=0)
        self.portal.manage_delObjects('sub1')
        self.failIf('sub1' in self.portal.objectIds())


def test_suite():
    from unittest import TestSuite, makeSuite
    suite = TestSuite()
    suite.addTest(makeSuite(TestPloneFolder))
    suite.addTest(makeSuite(TestCheckIdAvailable))
    suite.addTest(makeSuite(TestFolderListing))
    suite.addTest(makeSuite(TestManageDelObjects))
    suite.addTest(makeSuite(TestManageDelObjectsInPortal))
    return suite

if __name__ == '__main__':
    framework()
