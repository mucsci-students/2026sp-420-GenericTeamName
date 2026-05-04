import pytest
from unittest.mock import MagicMock, patch
from gui.proxy_manager import ProxyManager

class TestProxyManager:
    @pytest.fixture
    def mock_mw(self):
        """Creates a mock MainWindow with all standard expected methods."""
        mw = MagicMock()
        # Mock run_with_undo to execute the passed lambda immediately
        mw.run_with_undo = MagicMock(side_effect=lambda x: x())
        mw.viewer_mgr = MagicMock()
        mw.viewer_mgr.handle_change_path = MagicMock()
        mw.viewer_mgr._sync_detail_view = MagicMock()
        return mw

    @pytest.fixture
    def proxy(self, mock_mw):
        """Initializes ProxyManager with patched managers for every test."""
        with patch('gui.proxy_manager.ConfigManager'), \
             patch('gui.proxy_manager.ViewerManager'), \
             patch('gui.proxy_manager.FacultyManager'), \
             patch('gui.proxy_manager.CourseConfigManager'), \
             patch('gui.proxy_manager.RoomConfigManager'), \
             patch('gui.proxy_manager.LabConfigManager'), \
             patch('gui.proxy_manager.GenConfigManager'), \
             patch('gui.proxy_manager.TimeSlotEditor'), \
             patch('gui.proxy_manager.MeetingPatternEditor'), \
             patch('gui.proxy_manager.AIViewerManager'):
            return ProxyManager(mock_mw)

    def test_initialization(self, proxy, mock_mw):
        """Verify managers are created and config is loaded."""
        assert proxy.config_mgr is not None
        proxy.config_mgr.load.assert_called_once_with(mock_mw)
        assert "faculty_add" in proxy._registry

    def test_execute_invalid_action(self, proxy):
        """Verify returns False when action key is missing."""
        assert proxy.execute("non_existent_action") is False

    def test_execute_success_with_undo(self, proxy, mock_mw):
        """Full path: Registry exists -> Undo exists -> Sync exists."""
        mock_action = MagicMock()
        proxy._registry["test_act"] = mock_action
        
        result = proxy.execute("test_act", use_undo=True)
        
        assert result is True
        mock_mw.run_with_undo.assert_called_once()
        mock_action.assert_called_once_with(mock_mw)
        mock_mw.viewer_mgr._sync_detail_view.assert_called_once_with(mock_mw)

    def test_execute_success_no_undo_requested(self, proxy, mock_mw):
        """Path: use_undo is False, should skip run_with_undo."""
        mock_action = MagicMock()
        proxy._registry["test_act"] = mock_action
        
        result = proxy.execute("test_act", use_undo=False)
        
        assert result is True
        mock_mw.run_with_undo.assert_not_called()
        mock_action.assert_called_once_with(mock_mw)

    def test_execute_no_undo_method_on_mw(self, proxy, mock_mw):
        """Edge case: MainWindow is missing run_with_undo attribute."""
        del mock_mw.run_with_undo
        mock_action = MagicMock()
        proxy._registry["test_act"] = mock_action
        
        result = proxy.execute("test_act", use_undo=True)
        
        assert result is True
        mock_action.assert_called_once_with(mock_mw)

    def test_execute_no_sync_method_on_mw(self, proxy, mock_mw):
        """Edge case: MainWindow has no viewer_mgr (inspector sync is skipped)."""
        del mock_mw.viewer_mgr
        mock_action = MagicMock()
        proxy._registry["test_act"] = mock_action
        
        result = proxy.execute("test_act")
        
        assert result is True
        # Should not raise AttributeError

    def test_execute_exception_logged(self, proxy, mock_mw):
        """Verify error handling when a manager method crashes."""
        proxy.logger = MagicMock()
        mock_action = MagicMock(side_effect=ValueError("Test crash"))
        proxy._registry["fail_act"] = mock_action
        
        result = proxy.execute("fail_act", use_undo=False)
        
        assert result is False
        proxy.logger.error.assert_called()

    def test_lambda_save_config(self, proxy, mock_mw):
        """Test the lambda specifically for save_config."""
        result = proxy.execute("save_config", use_undo=False)
        assert result is True
        proxy.config_mgr.save.assert_called_once_with(mock_mw)

    def test_lambda_change_path(self, proxy, mock_mw):
        """Test the lambda specifically for change_path."""
        result = proxy.execute("change_path", use_undo=False)
        assert result is True
        mock_mw.viewer_mgr.handle_change_path.assert_called_once_with(mock_mw)

    def test_execute_with_args_and_kwargs(self, proxy, mock_mw):
        """Verify *args and **kwargs are passed through to the manager."""
        mock_action = MagicMock()
        proxy._registry["args_act"] = mock_action
        
        # Positional arguments must come before keyword arguments
        proxy.execute("args_act", False, "val1", key1="val2")
        
        # Verify the manager received (main_window, "val1", key1="val2")
        mock_action.assert_called_once_with(mock_mw, "val1", key1="val2")
