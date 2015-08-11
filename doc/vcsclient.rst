General VCS/SCM API
===================

.. currentmodule:: vcstools

The :class:`VcsClient` class provides a generic API for 

- Subversion (``svn``)
- Mercurial (``hg``)
- Git (``git``)
- Bazaar (``bzr``)



.. class:: VcsClient(vcs_type, path)

   API for interacting with source-controlled paths independent of
   actual version-control implementation.

   :param vcs_type: type of VCS to use (e.g. 'svn', 'hg', 'bzr', 'git'), ``str``
   :param path: filesystem path where code is/will be checked out , ``str``
    
   .. method:: path_exists() -> bool
    
      :returns: True if path exists on disk.

   .. method:: get_path() -> str
    
      :returns: filesystem path this client is initialized with.

   .. method:: url_matches(self, url, url_or_shortcut) -> bool

        client can decide whether the url and the other url are equivalent.
        Checks string equality by default

        :param url_or_shortcut: url or shortcut (e.g. bzr launchpad url)
        :returns: bool if params are equivalent

   .. method:: get_version([spec=None]) -> str
    
      :param spec: token for identifying repository revision
        desired.  Token might be a tagname, branchname, version-id,
        or SHA-ID depending on the VCS implementation.

        - svn: anything accepted by ``svn info --help``, 
          e.g. a ``revnumber``, ``{date}``, ``HEAD``, ``BASE``, ``PREV``, or
          ``COMMITTED``
        - git: anything accepted by ``git log``, e.g. a tagname,
          branchname, or sha-id.
        - hg: anything accepted by ``hg log -r``, e.g. a tagname, sha-ID,
          revision-number
        - bzr: revisionspec as returned by ``bzr help revisionspec``,
          e.g. a tagname or ``revno:<number>``

      :returns: current revision number of the repository.  Or if
        spec is provided, the globally unique identifier
        (e.g. revision number, or SHA-ID) of a revision specified by
        some token.

   .. method:: get_remote_version(self, fatch=False) -> str

        Find an identifier for the current revision on remote.
        Token spec might be a tagname,
        version-id, SHA-ID, ... depending on the VCS implementation.

        :param fetch: if False, only local information may be used
        :returns: current revision number of the remote repository.

   .. method:: get_current_version_label() -> str

      Find an description for the current local version.
      Token spec might be a branchname,
      version-id, SHA-ID, ... depending on the VCS implementation.

        :returns: short description of local version (e.g. branchname, tagename).

   .. method:: checkout(url, [version=''], [verbose=False], [shallow=False])

      Checkout the given URL to the path associated with this client.

      :param url: URL of source control to check out
      :param version: specific version to check out
      :param verbose: flag to run verbosely
      :param shallow: flag to create shallow clone without history

   .. method:: update(version)

      Update the local checkout from upstream source control.

   .. method:: detect_presence() -> bool

      :returns: True if path has a checkout with matching VCS type,
        e.g. if the type of this client is 'svn', the checkout at
        the path is managed by Subversion.
    
   .. method:: get_vcs_type_name() -> str
    
      :returns: type of VCS this client is initialized with.

   .. method:: get_url() -> str
    
      :returns: Upstream URL that this code was checked out from.

   .. method:: get_branch_parent()
    
      (Git Only)

      :returns: parent branch.

   .. method:: get_diff([basepath=None])

      :param basepath: compute diff relative to this path, if provided
      :returns: A string showing local differences

   .. method:: get_status([basepath=None, [untracked=False]])
    
      Calls scm status command. semantics of untracked are difficult
      to generalize. In SVN, this would be new files only. In git,
      hg, bzr, this would be changes that have not been added for
      commit.

      :param basepath: status path will be relative to this, if provided.
      :param untracked: If True, also show changes that would not commit
      :returns: A string summarizing locally modified files

