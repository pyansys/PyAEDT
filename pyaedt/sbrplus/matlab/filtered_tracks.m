function idx = filtered_tracks(rayhdm,unfiltered)
% FILTERED_TRACKS returns indices of unfiltered or filtered-out tracks
%
% Returns indices of ray tracks that will either be drawn
% (if unfiltered == true) or not drawn (if unfiltered == false).
%
% Input Params:
%  rayhdm (struct) ray bundle object returned by ld_sbrplushdm, must first be
%                  filtered using filter_rays1 or FILTERED_TRACKS throws an
%                  error
%
%  unfiltered (lgc) true = return indices of ray tracks to be drawn (DEFAULT)
%                   false = return indices of tracks filtered out
%
% Returns:
%  idx (Nx1 int) indices of trackes to be drawn or not drawn
%
% idx = FILTERED_TRACKS(rayhdm[,unfiltered])
%
% COPYRIGHT ANSYS, Inc. ALL RIGHTS RESERVED.

if ~exist('unfiltered','var') unfiltered = true; end

% verify the ray bundle has been passed through filter_rays1()
bundle = rayhdm.hdm;
errIdBadInp = 'filtered_tracks:badInput';
errMsg = ['Passed in ray bundle must be post-processed using ' ...
          'filter_rays1.m before rays can be rendered.'];
if ~isfield(bundle.hdmObj,'filter')
  error(errIdBadInp,errMsg);
end
if ~strcmp(bundle.hdmObj.filter,'filter_rays1')
  error(errIdBadInp,errMsg);
end

Ntrack = length(bundle.hdmObj.ray_tracks);
idx = [];
for itrack = 1:Ntrack
  rt0 = bundle.hdmObj.ray_tracks(itrack);
  drawBranch = rt0.hdmObj.source_bounce.hdmObj.drawBranch;
  if ~xor(unfiltered,drawBranch)
    idx = [idx;itrack];
  end
end

end  % filtered_tracks