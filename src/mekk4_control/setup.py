from setuptools import find_packages, setup

package_name = 'mekk4_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='ubuntu',
    maintainer_email='gruppe5pi5@users.noreply.github.com',
    description='Control nodes and interfaces for the MEKK4 robot.',
    license='MIT',
    entry_points={
        'console_scripts': [
        ],
    },
)
