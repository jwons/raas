function provenance_collector(path)
  import org.dataone.client.run.RunManager;
  mgr = RunManager.getInstance();
  mgr.configuration.capture_yesworkflow_comments=0;
  mgr.record(path,path);
end
