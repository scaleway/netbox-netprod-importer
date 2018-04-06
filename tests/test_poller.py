import pytest

from netbox_netprod_importer.poller import DevicePoller


class TestPoller():
    @pytest.fixture(autouse=True)
    def build_poller(self):
        self.poller = DevicePoller()
