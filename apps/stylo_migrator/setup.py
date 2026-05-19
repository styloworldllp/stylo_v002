from setuptools import setup, find_packages

setup(
    name="stylo_migrator",
    version="1.0.0",
    description="ERPNext v14 → v16 Data Migration Tool for Styloworld",
    author="Styloworld",
    author_email="admin@styloworld.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=["pymysql"],
)
