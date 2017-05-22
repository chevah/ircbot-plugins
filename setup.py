from setuptools import Command, find_packages, setup
import os

VERSION = '0.1.0'


class PublishCommand(Command):
    """
    Publish the source distribution to private Chevah PyPi server.
    """

    user_options = []

    def initialize_options(self):
        self.cwd = None

    def finalize_options(self):
        self.cwd = os.getcwd()

    def run(self):
        if (os.getcwd() != self.cwd):
            raise AssertoinError('Must be in package root: %s' % self.cwd)
        self.run_command('bdist_wheel')
        # Upload package to Chevah PyPi server.
        upload_command = self.distribution.get_command_obj('upload')
        upload_command.repository = u'chevah'
        self.run_command('upload')

data_files = []

for root, folders, files in os.walk('limnoria-plugins'):
    members = [os.path.join(root, name) for name in files]
    data_files.append((root, members))

distribution = setup(
    name="chevah-ircbot-plugins",
    version=VERSION,
    maintainer='Adi Roiban',
    maintainer_email='adi.roiban@chevah.com',
    license='MIT',
    platforms='any',
    description="Plugins for IRCBot used by the Chevah Project.",
    long_description="",
    url='http://www.chevah.com',
    namespace_packages=['chevah'],
    packages=find_packages('.'),
    install_requires=[
        'limnoria==2017.03.30',
        'google-api-python-client',
        ],
    extras_require = {
        'dev': [
            'mock',
            'nose',
            'pyflakes',
            'pep8',
            ],
    },
    test_suite = 'chevah.ircbot_plugins.tests',
    cmdclass={
        'publish': PublishCommand,
        },
    data_files=data_files
    )
