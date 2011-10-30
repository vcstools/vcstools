        self.root_directory = tempfile.mkdtemp()
        self.directories = dict(setUp=self.root_directory)
        self.remote_path = os.path.join(self.root_directory, "remote")
        os.makedirs(self.remote_path)
        subprocess.check_call(["git", "init"], cwd=self.remote_path)
        subprocess.check_call(["touch", "fixed.txt"], cwd=self.remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=self.remote_path)
        subprocess.check_call(["git", "tag", "test_tag"], cwd=self.remote_path)
        subprocess.check_call(["git", "branch", "test_branch"], cwd=self.remote_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.remote_path, stdout=subprocess.PIPE)
        subprocess.check_call(["touch", "modified.txt"], cwd=self.remote_path)
        subprocess.check_call(["touch", "modified-fs.txt"], cwd=self.remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "initial"], cwd=self.remote_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.remote_path, stdout=subprocess.PIPE)
        subprocess.check_call(["touch", "deleted.txt"], cwd=self.remote_path)
        subprocess.check_call(["touch", "deleted-fs.txt"], cwd=self.remote_path)
        subprocess.check_call(["git", "add", "*"], cwd=self.remote_path)
        subprocess.check_call(["git", "commit", "-m", "modified"], cwd=self.remote_path)
        po = subprocess.Popen(["git", "log", "-n", "1", "--pretty=format:\"%H\""], cwd=self.remote_path, stdout=subprocess.PIPE)
        subprocess.check_call(["git", "tag", "last_tag"], cwd=self.remote_path)
        
        
    
        local_path = os.path.join(self.root_directory, "ros")
        url = self.remote_path
        client = GitClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url))
        self.assertEqual(client.get_url(), self.remote_path)
        local_path = os.path.join(self.root_directory, "ros")
        url = self.remote_path
        local_path = os.path.join(self.root_directory, "ros")
        url = self.remote_path


    def test_checkout_master_branch_and_update(self):
        from vcstools.git import GitClient
        subdir = "checkout_specific_version_test"
        local_path = os.path.join(self.root_directory, "ros")
        url = self.remote_path
        branch = "master"
        client = GitClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, branch))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_branch_parent(), branch)
        self.assertTrue(client.update(branch))
        self.assertEqual(client.get_branch_parent(), branch)

        local_path = os.path.join(self.root_directory, "ros")
        url = self.remote_path
        branch = "test_branch"
        new_branch = 'master'
        self.assertFalse(client.update(new_branch))
        self.assertEqual(client.get_branch_parent(), branch)


    def test_checkout_specific_tag_and_update(self):
        from vcstools.git import GitClient
        local_path = os.path.join(self.root_directory, "ros")
        url = self.remote_path
        tag = "last_tag"
        client = GitClient(local_path)
        self.assertFalse(client.path_exists())
        self.assertFalse(client.detect_presence())
        self.assertTrue(client.checkout(url, tag))
        self.assertTrue(client.path_exists())
        self.assertTrue(client.detect_presence())
        self.assertEqual(client.get_path(), local_path)
        self.assertEqual(client.get_url(), url)
        self.assertEqual(client.get_branch_parent(), None)
        tag = "test_tag"
        self.assertTrue(client.update(tag))
        self.assertEqual(client.get_branch_parent(), None)
        
        tag = "test_tag"
        # so far, once we track a branch, we cannot move off it
        self.assertFalse(client.update(tag))


        self.readonly_path = os.path.join(self.root_directory, "readonly")
        from vcstools.git import GitClient
        client = GitClient(self.readonly_path)
        self.assertTrue(client.checkout(self.remote_path, self.readonly_version))


