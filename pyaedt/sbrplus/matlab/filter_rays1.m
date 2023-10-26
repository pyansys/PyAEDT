function fltrCfg = filter_rays1(rayhdm,fltrCfg)
% FILTER_RAYS1 apply configurable filter to rays
%
% Adds drawBounce, drawTransEscape, drawReflEscape, and drawBranch logical
% fields to each ray bounce HmdObject within rayhdm, setting them according
% to the filter configuration of fltrCfg.
%
% Adds a source_bounce HdmObject to each ray track and a parent field to each
% ray bounce HdmObject to provide access to bounce ancestors. For UTD
% ray tracks, adds a ray bounce HdmObject for the diffraction point that
% sits between the source bounce and the first bounce.
%
% In addition, adds the following properties to each ray bounce HdmObject:
%  .cumulative_dist (dbl) path length from source up to current bounce,
%                         measured from phase ref. plane in case of plane-wave
%                         incidence
%
%  .isLeaf    (lgc) true if ray bounce is a leaf bounce, meaning it
%                   either has at least one escaping ray or it has no
%                   descendant bounces
%
%  .maxDepth  (int) maximum tree depth reached by following all descendant
%                   bounces and escaping rays to their leaves
%
%  .maxTDepth (int) maximum transmission depth reached by following ...
%
%  .maxRDepth (int) maximum reflection depth reached by following ...
%
%  .branches (1xNb int) indices of all branches joining the bounce from among
%                       all descendants, refs .track_leaves vector of leaf
%                       bounces added to its parent ray track object
%
% Adds the following properties to each ray track HdmObject:
%  .track_leaves (1xNb HdmObject) leaf bounce of each tree branch, the indices
%                held in .branches of each ray bounce pertain to this vector of
%                branch leaf bounces
%
%  .pwinc_theta_phi_deg (1x2 dbl) [theta phi] incident plane wave angle [deg],
%                only added if ray bundle source_type is PLANE_WAVE, angles
%                inferred by vector from ray launch point to first hit point
%                or UTD diffraction point
%
% Adds the following properties to each ray bundle HdmObject:
%  .pwinc_map (map,            containers.Map object whose integer keys match
%              int -> 1x2 dbl) sweep_angle_index field found in each track of
%             monostatic plane wave ray bundle, each value [theta phi] of
%             incidence angle [deg], has one value at index 0 for bistatic RCS,
%             only included if bundle source_type is PLANE_WAVE, useful for
%             setting fltrCfg.idxAng in subsequent calls to FILTER_RAYS1
%
% rayhdm is the return value of ld_sbrplushdm when loading SBR+ exported
% rays. There is no return value for FILTER_RAYS1. Rather, it uses the
% HdmObject handle object framework of rayhdm to modify the contents of the
% passed-in rayhdm, even though rayhdm is passed by value to this function
% according to the usual MATLAB behavior.
%
% Input Params:
%  rayhdm (struct) ray bundle object returned by ld_sbrplushdm AS AN HdmObject
%                  (call with ld_sbrplushdm with asStruct set to FALSE)
%
%  fltrCfg (struct) filter settings
%   .depthRng  (1x2 int) [min max] bounce depth range, DEFAULT = [0 1000000],
%                        launch point and first bounce have bounce depths of
%                        0 and 1, respectively, bounce-level filter
%
%   .rDepthRng (1x2 int) [min max] refl. depth range, DEFAULT = [0 1000000],
%                        first bounce has a reflection depth of 0, and after
%                        reflecting there, the next bounce has a refl. depth
%                        of 1, bounce-level filter
%
%   .tDepthRng (1x2 int) [min max] trans. depth range, DEFAULT = [0 1000000],
%                        first bounce has a transmission depth of 0, and after
%                        penetrating there, the next bounce has a trans. depth
%                        of 1, track bounce-level filter
%
%   .NreflRng  (1x2 int) [min max] range for total number of reflections before
%                        terminating or escaping, controls branch-level filter,
%                        DEFAULT = [0 1000000]
%
%   .NtransRng (1x2 int) [min max] range for total number of reflections before
%                        terminating or escaping, track branch-level filter,
%                        DEFAULT = [0 1000000]
%
%   .trackType {1xN cell} a cell array of strings {'SBR', 'UTD'} for ray track
%                OR (str) types to include, DEFAULT = [] = include all types,
%                         accepts simple char string to specify a single type
%
%   .idxAng    (1xM int) list of monostatic sweep angle indices to include,
%                        ignored for ray bundles from antenna sources and
%                        bi-static RCS since only monostatic RCS ray bundles
%                        include/need a sweep angle index, DEFAULT = [] =
%                        include all incident angles, see above regarding
%                        .pwinc_map added to ray bundle HmdObject
%
% Returns:
%  fltrCfg (struct) copy of input fltrCfg augmented with default values where
%                   applicable and with any unrecognized struct fields removed
%
%  Note: filtered rays are returned via modifications to HdmObject handle
%        objects in rayhdm
%
%                   Summary of Input fltrCfg Struct Fields
% =============================================================================
% | Field Name |     Type     |                Allowed Values                 |
% |            |              |    entry before semicolon is the default      |
% |============+==============+===============================================+
% | depthRng   |    1x2 int   | [0 1000000]; [min max], min,max:[0, inf)      |
% | rDepthRng  |    1x2 int   | same                                          |
% | tDepthRng  |    1x2 int   | same                                          |
% | NreflRng   |    1x2 int   | same                                          |
% | NtransRng  |    1x2 int   | same                                          |
% | trackType  | 1xN cell/str | [] (all types); SBR, UTD, {SBR, UTD}          |
% | idxAng     |    1xM int   | [] (all angles); [0, inf)                     |
% =============================================================================
%
% fltrCfg = FILTER_RAYS1(rayhdm[,fltrCfg])
%
% COPYRIGHT ANSYS, Inc. ALL RIGHTS RESERVED.

% populate optional filter settings with default values
if ~exist('fltrCfg','var') fltrCfg = []; end

if ~isfield(fltrCfg,'depthRng') fltrCfg.depthRng = []; end
if isempty(fltrCfg.depthRng) fltrCfg.depthRng = [0 1000000]; end

if ~isfield(fltrCfg,'rDepthRng') fltrCfg.rDepthRng = []; end
if isempty(fltrCfg.rDepthRng) fltrCfg.rDepthRng = [0 1000000]; end

if ~isfield(fltrCfg,'tDepthRng') fltrCfg.tDepthRng = []; end
if isempty(fltrCfg.tDepthRng) fltrCfg.tDepthRng = [0 1000000]; end

if ~isfield(fltrCfg,'NreflRng') fltrCfg.NreflRng = []; end
if isempty(fltrCfg.NreflRng) fltrCfg.NreflRng = [0 1000000]; end

if ~isfield(fltrCfg,'NtransRng') fltrCfg.NtransRng = [0 1000000]; end
if isempty(fltrCfg.NtransRng) fltrCfg.NtransRng = [0 1000000]; end

if ~isfield(fltrCfg,'trackType') fltrCfg.trackType = []; end
if isempty(fltrCfg.trackType) fltrCfg.trackType = {'SBR','UTD'}; end
if ischar(fltrCfg.trackType)
  % .trackType is char array, place in 1x1 cell array
  fltrCfg.trackType = {fltrCfg.trackType};
end

if ~isfield(fltrCfg,'idxAng') fltrCfg.idxAng = []; end

% validate and update fltrCfg fields
valid_flds = {'depthRng','rDepthRng','tDepthRng','NreflRng','NtransRng', ...
              'trackType','idxAng'};
fltrCfg = validate_sfields(fltrCfg,valid_flds,'fltrCfg');

% perform checks on rayhdm input
if ~isstruct(rayhdm)
  error('filter_rays1:badInput',...
        ['Input argument rayhdm does not appear to be a return value ' ...
         'from ld_sbrplushdm.m since it is not a MATLAB struct']);
end
if ~isfield(rayhdm,'hdm')
  if isfield(rayhdm,'export_type')
    error('filter_rays1:badInput',...
          ['Input struct rayhdm appears to be the return value from ' ...
           'ld_sbrplushdm.m, but lacks a .hdm struct field. Try loading ' ...
           'the ray export file again, this time calling ld_sbrplushdm.m ' ...
           'with asStruct input arg set to false.']);

  else
    error('filter_rays1:badInput',...
          ['Input struct rayhdm does not appear to be a return value ' ...
           'from ld_sbrplushdm.m']);
  end
end

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function recurse_track(rb,rbParent,pushFunc,popFunc)
  % recursively descend through ray track and apply "push" or "pop" operations
  % at each bounce along the way
  %
  % Input Params:
  %  rb       (HdmObject) current ray bounce to process
  %  rbParent (HdmObject) parent of current ray bounce, pass zero (0) if no
  %              OR 0     parent to this ray bounce
  %
  %  pushFunc (func ptr) function that accepts current and parent bounce
  %                      HdmObjects as its two arguments, invoked before
  %                      recursively descending further in ray-track tree,
  %                      pass zero (0) to skip
  %
  %  popFunc  (func ptr) function that accepts current and parent bounce
  %                      HdmObjects as its two arguments, invoked AFTER
  %                      recursively and fully descending further in ray-track
  %                      tree, pass zero (0) to skip
  %
  % recurse_track(rb,rbParent,pushFunc,popFunc)
  if isa(pushFunc,'function_handle')
    pushFunc(rb,rbParent);
  end

  % track type filter goes here

  rbNext = rb.hdmObj.trans_bounce;
  if ~isempty(rbNext)
    depth = depth + 1;
    tDepth = tDepth + 1;
    recurse_track(rbNext,rb,pushFunc,popFunc);
    depth = depth - 1;
    tDepth = tDepth - 1;
  end

  rbNext = rb.hdmObj.refl_bounce;
  if ~isempty(rbNext)
    depth = depth + 1;
    isSurfBnc = (rb.hdmObj.bounce_type == SbrBounceType.Surface);
    if isSurfBnc
      rDepth = rDepth + 1;
    end
    recurse_track(rbNext,rb,pushFunc,popFunc);
    depth = depth - 1;
    if isSurfBnc
      rDepth = rDepth - 1;
    end
  end

  if isa(popFunc,'function_handle');
    popFunc(rb,rbParent);
  end
  
  end  % recurse_track

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function init_draw_flags(rb,rbParent)
  % initialize all ray bounce and branch draw flags to false
  %
  % Also assigns parent (rbParent) to current ray bounce (rb), providing a
  % connection to its ancestors, and assigns bounce_type = SbrBounce.Surface
  % enumeration if bounce_type is not already defined.
  %
  % Serves as push or pop function callable from recurse_track.
  %
  % Input Params:
  %  rb       (HdmObject) current ray bounce
  %  rbParent (HdmObject) parent ray bounce, pass zero (0) if current ray
  %                       bounce has no parent (i.e., at top of ray track
  %                       tree)
  %
  % Returns: (nothing)
  rb.hdmObj.parent = rbParent;
  if ~isfield(rb.hdmObj,'bounce_type')
    rb.hdmObj.bounce_type = SbrBounceType.Surface;  % enum
  end

  if ~isnumeric(rbParent)
    % current bounce has parent bounce
    hitDist = rb.hdmObj.hit_pt - rbParent.hdmObj.hit_pt;
    hitDist = sqrt(dot(hitDist,hitDist));
    rb.hdmObj.cumulative_dist = rbParent.hdmObj.cumulative_dist + hitDist;
  end

  rb.hdmObj.drawBounce = false;
  rb.hdmObj.drawTransEscape = false;
  rb.hdmObj.drawReflEscape = false;
  rb.hdmObj.drawBranch = false;

  end  % init_draw_flags

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function update_branch_info(rb,rbParent)
  % add bounce properties pertaining to its state within the ray track tree
  %
  % The following bounce properties are added to rb.hdmObj:
  % - isLeaf   true if rb is a leaf bounce (see below)
  % - maxDepth maximum bounce depth reached following all descendant bounces
  %            and escaping rays to their leaves
  % - maxTDepth maximum transmission depth reached following all ...
  % - maxRDepth maximum reflection depth reached following all ...
  % - branches  indices (see below) of all branches joining rb from among all
  %             descendants
  %
  % The following definition of a leaf bounce has arbitrary aspects that
  % serve the purpose in which it used.
  %   Any bounce with an escaping ray, whether on reflection or transmission
  %   side, is deemed a leaf bounce, even if it has a descendant bounce on the
  %   other side from the escaping ray. If the bounce has no escaping rays,
  %   then the presence of a descendant bounce on either the reflection or
  %   transmission side means it is not a leaf bounce.
  %
  % This method modifies the exterior variable, track_leaves. If rb is a leaf
  % bounce, then the row vector track_leaves will be appended with rb, a
  % handle object. The branch index of the rb leaf bounce will then be its
  % position in the track_leaves vector. This will become the first index
  % in branches (see above), which will then be appended with branch indices
  % for any descendant bounces. If rb is not a leaf bounce, its branches will
  % be the combination of branch indices from descendant bounces.
  %
  % Serves as pop function callable from recurse_track. This means this
  % function should only be called for a given ray bounce after it has first
  % been called for all descendant bounces.
  %
  % Input Params:
  %  rb       (HdmObject) current ray bounce
  %  rbParent (HdmObject) parent ray bounce, ignored

  hasTransBnc    = rb.hdmObj.flags.HasTransBnc;
  hasReflBnc     = rb.hdmObj.flags.HasReflBnc;
  hasTransEscRay = rb.hdmObj.flags.HasTransEscRay;
  hasReflEscRay  = rb.hdmObj.flags.HasReflEscRay;

  isLeaf = hasTransEscRay || hasReflEscRay || ~(hasTransBnc || hasReflBnc);
  rb.hdmObj.isLeaf = isLeaf;

  branches = [];
  if isLeaf
    % LEAF BOUNCE
    % - has escaping trans ray OR escaping refl ray OR
    % - has no descendant bounces (i.e., terminal hit point)
    track_leaves = [track_leaves rb];
    branches = length(track_leaves);
    maxCumulativeDist = max(maxCumulativeDist,rb.hdmObj.cumulative_dist);
  end

  maxDepth = 0;
  maxTDepth = 0;
  maxRDepth = 0;
  if hasTransBnc
    tBnc = rb.hdmObj.trans_bounce;
    maxDepth = tBnc.hdmObj.maxDepth;
    maxTDepth = tBnc.hdmObj.maxTDepth;
    maxRDepth = tBnc.hdmObj.maxRDepth;
    branches = [branches tBnc.hdmObj.branches];
  end
  if hasReflBnc
    rBnc = rb.hdmObj.refl_bounce;
    maxDepth = max(maxDepth,rBnc.hdmObj.maxDepth);
    maxTDepth = max(maxTDepth,rBnc.hdmObj.maxTDepth);
    maxRDepth = max(maxRDepth,rBnc.hdmObj.maxRDepth);
    branches = [branches rBnc.hdmObj.branches];
  end
  if hasTransEscRay
    maxDepth = max(maxDepth,depth + 1);
    maxTDepth = max(maxTDepth,tDepth + 1);
  end
  if hasReflEscRay
    maxDepth = max(maxDepth,depth + 1);
    maxRDepth = max(maxRDepth,rDepth + 1);
  end
  rb.hdmObj.maxDepth = maxDepth;
  rb.hdmObj.maxTDepth = maxTDepth;
  rb.hdmObj.maxRDepth = maxRDepth;
  rb.hdmObj.branches = branches;
  end  % update_branch_info

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function set_draw_branch(rb,rbParent)
  % set draw-branch flag for ray bounce at ray-track leaf bounce
  % and propagate it up-tree if setting true
  %
  % If rb is not a leaf bounce, does nothing. Assumes draw-branch flag
  % of rb was initialized to false. If the conditions for drawing the
  % branch are not satisfied by leaf-bounce rb, then this method makes
  % no change to its draw-branch flag or that of its ancestors.
  %
  % Serves as push or pop function callable from recurse_track.
  %
  % Input Params:
  %  rb       (HdmObject) current ray bounce
  %  rbParent (HdmObject) ignored
  %
  % Returns: (nothing)
  if ~draw_branch(rb)
    % We are not drawing this ray branch on account of props of this
    % putative leaf bounce. Don't change the state of its draw-branch
    % flag to false, just leave it alone. It may have have been set
    % true if it's a ray-track branch merge point and the other
    % branch hanging off it had already been set to be drawn.
    return;
  end

  % set drawBranch flag for this bounce and propagate this up-tree
  rb.hdmObj.drawBranch = true;
  while isa(rb.hdmObj.parent,'HdmObject')
    rb = rb.hdmObj.parent;
    rb.hdmObj.drawBranch = true;
  end
  end  % set_draw_branch

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function drawBranch = draw_branch(rb)
  % returns true if branch identified by specified leaf bounce should be drawn
  % based on the current filter settings
  %
  % Applies whole-track filters: fltrCfg.NreflRng, fltrCfg.NtransRng.
  %
  % Support function for set_draw_branch(). Always returns false if rb is not a
  % leaf bounce.
  drawBranch = false;
  if ~rb.hdmObj.isLeaf
    % if we have already determined that track type is mismatched,
    % return early as false
    return;
  end

  reflEscaped = rb.hdmObj.flags.HasReflEscRay;
  if reflEscaped
    rDepth0 = rDepth + 1;
    drawBranch = rDepth0 >= fltrCfg.NreflRng(1) && ...
                 rDepth0 <= fltrCfg.NreflRng(2) && ...
                 tDepth >= fltrCfg.NtransRng(1) && ...
                 tDepth <= fltrCfg.NtransRng(2);
    if drawBranch
      return;  % early return possible
    end
  end

  transEscaped = rb.hdmObj.flags.HasTransEscRay;
  if transEscaped
    tDepth0 = tDepth + 1;
    drawBranch = tDepth0 >= fltrCfg.NtransRng(1) && ...
                 tDepth0 <= fltrCfg.NtransRng(2) && ...
                 rDepth >= fltrCfg.NreflRng(1) && ...
                 rDepth <= fltrCfg.NreflRng(2);
    if drawBranch
      return;  % early return possible
    end
  end

  if reflEscaped || transEscaped
    % Since this leaf bounce is not terminal, if we did not early-return by
    % this point, then branch should not be drawn.
    return;
  end

  % This leaf bounce is terminal: either absorbed or reached max num. bounces.
  drawBranch = rDepth >= fltrCfg.NreflRng(1) && ...
               rDepth <= fltrCfg.NreflRng(2); 
  if ~drawBranch
    return;
  end

  drawBranch = tDepth >= fltrCfg.NtransRng(1) && ...
               tDepth <= fltrCfg.NtransRng(2); 
  if ~drawBranch
    return;
  end

  % leaf bounce survived all filters, so draw its branch
  drawBranch = true;
  
  end  % draw_branch

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function set_draw_flags(rb,rbParent)
  % set draw-bounce flags of current bounce based on filter settings
  %
  % Controls the drawBounce, drawReflEscape, and drawTransEscape flags
  % of current ray-bounce.
  %
  % Serves as push or pop function callable from recurse_track.
  %
  % Input Params:
  %  rb       (HdmObject) current ray bounce
  %  rbParent (HdmObject) ignored
  %
  % Returns: (nothing)
  if ~rb.hdmObj.drawBranch
    % already determined this branch or merged branches at this level
    % should not be drawn -->
    %  early return, ensures draw-bounce flags cannot be set true
    return;
  end

  rb.hdmObj.drawBounce = draw_bounce(rb);
  rb.hdmObj.drawTransEscape = draw_trans_escape(rb);
  rb.hdmObj.drawReflEscape = draw_refl_escape(rb);
  end  % set_draw_flags

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function drawBounce = draw_bounce(rb)
  % returns true if current bounce in ray-track tree should be drawn based
  % on filter settings
  %
  % Applies bounce-level filters: fltrCfg.depthRng, .rDepthRng, .tDepthRng.
  %
  % Support function for set_draw_flags().
  drawBounce = depth >= fltrCfg.depthRng(1) && ...
               depth <= fltrCfg.depthRng(2) && ...
               rDepth >= fltrCfg.rDepthRng(1) && ...
               rDepth <= fltrCfg.rDepthRng(2) && ...
               tDepth >= fltrCfg.tDepthRng(1) && ...
               tDepth <= fltrCfg.tDepthRng(2);
  end  % draw_bounce

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function drawTrans = draw_trans_escape(rb)
  % returns true if escaping transmission ray should be drawn from current
  % ray bounce
  %
  % Returning true requires:
  %  - ray bounce has an escaping transmission ray
  %  - reflection depth of ray bounce is within fltrCfg.NreflRng BRANCH filter
  %  - transmission depth of ray bounce PLUS ONE is within fltrCfg.NtransRng
  %    BRANCH filter
  %
  %  - composite depth of ray bounce PLUS ONE is within fltrCfg.depthRng
  %    BOUNCE filter
  %
  %  - reflection depth of ray bounce is within fltrCfg.rDepthRng BOUNCE filter
  %
  %  - transmission depth of ray bounce PLUS is within fltrCfg.tDepthRng
  %    BOUNCE filter
  %
  % Support function for set_draw_flags().
  drawTrans = false;
  if ~rb.hdmObj.flags.HasTransEscRay
    return;
  end
  depth0 = depth + 1;
  tDepth0 = tDepth + 1;
  drawTrans = tDepth0 >= fltrCfg.NtransRng(1) && ...
              tDepth0 <= fltrCfg.NtransRng(2) && ...
              rDepth >= fltrCfg.NreflRng(1) && ...
              rDepth <= fltrCfg.NreflRng(2) && ...
              depth0 >= fltrCfg.depthRng(1) && ...
              depth0 <= fltrCfg.depthRng(2) && ...
              rDepth >= fltrCfg.rDepthRng(1) && ...
              rDepth <= fltrCfg.rDepthRng(2) && ...
              tDepth0 >= fltrCfg.tDepthRng(1) && ...
              tDepth0 <= fltrCfg.tDepthRng(2);
  end  % draw_trans_escape

  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
  function drawRefl = draw_refl_escape(rb)
  % returns true if escaping reflection ray should be drawn from current
  % ray bounce
  %
  % Uses corresponding criteria employed by draw_trans_escape().
  % Support function for set_draw_flags().
  drawRefl = false;
  if ~rb.hdmObj.flags.HasReflEscRay
    return;
  end
  depth0 = depth + 1;
  rDepth0 = rDepth + 1;
  drawRefl = rDepth0 >= fltrCfg.NreflRng(1) && ...
             rDepth0 <= fltrCfg.NreflRng(2) && ...
             tDepth >= fltrCfg.NtransRng(1) && ...
             tDepth <= fltrCfg.NtransRng(2) && ...
             depth0 >= fltrCfg.depthRng(1) && ...
             depth0 <= fltrCfg.depthRng(2) && ...
             rDepth0 >= fltrCfg.rDepthRng(1) && ...
             rDepth0 <= fltrCfg.rDepthRng(2) && ...
             tDepth >= fltrCfg.tDepthRng(1) && ...
             tDepth <= fltrCfg.tDepthRng(2);
  end  % draw_trans_escape
  %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

bundle = rayhdm.hdm;  % HdmObject
Ntrack = length(bundle.hdmObj.ray_tracks);

% build the (partial) structure of a bounce object to serve as the source
% "bounce" parent of each first_bounce HdmObject among the ray tracks
%
% Introducing a source "bounce" this way simplifies the code logic of other
% post-processing functions like draw_rays2.m.
hdmStruct.flags.HasTransBnc = false;
hdmStruct.flags.HasTransEscRay = false;
hdmStruct.flags.HasReflBnc = false;
hdmStruct.flags.HasReflEscRay = false;

hdmStruct.hit_pt = [];  % set to source_point of each ray track
hdmStruct.footprint_vertices = [];
hdmStruct.trans_bounce = [];
hdmStruct.trans_escaped_ray = [];
hdmStruct.refl_bounce = []; % set to first_bounce of each ray track
hdmStruct.refl_escaped_ray = [];
hdmStruct.parent = [];
hdmStruct.bounce_type = SbrBounceType.Undefined;  % enumeration
hdmStruct.cumulative_dist = 0;

% Test if ray bundle has already been filtered by filter_rays1().
%
% The same ray bundle can be filtered multiple times with filter_rays1,
% applying a different filter each time to achieve a different outcome.
% If the ray bundle has already been filtered, we can/must skip any
% one-time mods to either save effort or avoid corrupting the tracks:
% -  skip introduction of a source bounce HdmObject since it should already
%    be there
%
% - skip calling update_branch_info as pop-function on first pass through
%   track tree to spare wasted effort
%
% See later where .filter field is added to bundle.hdmObj after all the
% filtering is done. The following check needs to be kept consistent
% with that.
filter_func_name = 'filter_rays1';
alreadyFiltered = isfield(bundle.hdmObj,'filter');
if alreadyFiltered
  alreadyFiltered = strcmp(bundle.hdmObj.filter,filter_func_name);
end

r2d = 180/pi;
isPwSource = strcmp(bundle.hdmObj.source_type,'PLANE_WAVE');
rt1 = bundle.hdmObj.ray_tracks(1);
hasSweepAngIdx = isfield(rt1.hdmObj,'sweep_angle_index');
filterSweepIdx = hasSweepAngIdx && ~isempty(fltrCfg.idxAng);
sweepAngIdxMap = containers.Map('KeyType','int32','ValueType','any');
                 % sweep_angle_index -> [theta phi]

% set flags for track_type filter
includeSbr = false;
includeUtd = false;
for trackType0 = fltrCfg.trackType
  switch lower(trackType0{1})
   case 'sbr'
    includeSbr = true;
   case 'utd'
    includeUtd = true;
   otherwise
    error('filter_rays1:badInput',...
          'Unrecognized track type in fltrCfg.trackType: %s',trackType0{1});
  end
end

minFpDistBundle = realmax;  % largest double FP number
maxDistBundle = 0;
for itrack = 1:Ntrack
  rbSrc = [];
  rbUtd = [];
  rt0 = bundle.hdmObj.ray_tracks(itrack);
  first_bounce = rt0.hdmObj.first_bounce;
  % The source bounce will be added if
  % - the ray bundle has not already been filtered by filter_rays1(),
  %   which will often be the case
  %
  % - in spite of the ray bundle already having been filtered by filter_rays1()
  %   the ray track somehow does not have a .source_bounce field, which is
  %   not expected
  addSrcBnc = ~alreadyFiltered || ~isfield(rt0.hdmObj,'source_bounce');

  if addSrcBnc
    % Introduce source "bounce" HdmObject to top of ray track, and set its
    % refl_bounce to the first_bounce or, if applicable, the UTD edge
    % diffraction bounce.
    rbSrc = HdmObject(hdmStruct);
    rbSrc.hdmObj.hit_pt = rt0.hdmObj.source_point;
    rbSrc.hdmObj.bounce_type = SbrBounceType.Source;  % enum

    if isfield(rt0.hdmObj,'launch_offset_dist')
      % Init cumulative dist at source bounce to launch_offset_dist of ray
      % track. Cumulative dist of any descendants will automatically update
      % during tree recursion.
      rbSrc.hdmObj.cumulative_dist = rt0.hdmObj.launch_offset_dist;
    end

    utd_point = rt0.hdmObj.utd_point;
    if ~isempty(utd_point)
      % There's a UTD diffraction. Represent this as a bounce whose parent
      % is the source bounce and whose reflection side bounce is the first
      % bounce.
      rbUtd = HdmObject(hdmStruct);
      rbUtd.hdmObj.flags.HasReflBnc = true;  % so rbUtd won't be marked as leaf
      rbUtd.hdmObj.hit_pt = utd_point;
      rbUtd.hdmObj.refl_bounce = first_bounce;
      rbUtd.hdmObj.bounce_type = SbrBounceType.UtdEdge;  % enumeration

      rbSrc.hdmObj.flags.HasReflBnc = true;  % so rbSrc won't be marked as leaf
      rbSrc.hdmObj.refl_bounce = rbUtd;

    else
      % no UTD diffraction
      rbSrc.hdmObj.flags.HasReflBnc = true;
      rbSrc.hdmObj.refl_bounce = first_bounce;
    end

    if isPwSource
      % determine incidence angle and add this info to rayrack in map from
      % sweep_angle_index to [theta phi] angle
      %
      % Following is vector from either first bounce or UTD point to source.
      % It points toward the PW source.
      vInc = rbSrc.hdmObj.hit_pt - rbSrc.hdmObj.refl_bounce.hdmObj.hit_pt;
      [theta phi] = rvec2thetaphi(vInc);
      theta_phi_deg = [theta phi]*r2d;
      rt0.hdmObj.pwinc_theta_phi_deg = theta_phi_deg;

      idxSweepAng = int32(0);
      if hasSweepAngIdx
        idxSweepAng = rt0.hdmObj.sweep_angle_index;
      end
      sweepAngIdxMap(idxSweepAng) = theta_phi_deg;
    end
    rt0.hdmObj.source_bounce = rbSrc;
  
  else
    % Ray track already has source bounce. No need to create it.
    rbSrc = rt0.hdmObj.source_bounce;
  end

  % First-pass tree recursion: init draw flags and, if first time to filter
  % ray bundle, determine and cache track properties.
  rDepth = 0;
  tDepth = 0;
  depth = 0;
  if alreadyFiltered
    recurse_track(rbSrc,0,@init_draw_flags,0);
  else
    track_leaves = [];
    maxCumulativeDist = 0;
    recurse_track(rbSrc,0,@init_draw_flags,@update_branch_info);
    rt0.hdmObj.track_leaves = track_leaves;
    rt0.hdmObj.max_cumulative_dist = maxCumulativeDist;
    maxDistBundle = max(maxDistBundle,maxCumulativeDist);
    minFpDistBundle = ...
      min(minFpDistBundle,first_bounce.hdmObj.cumulative_dist);
  end

  % At this point, all the track bounces have their draw flags added and
  % set to false, and metrics like maxDepth have been added. Test if ray
  % track type matches those in fltrCfg.trackType, and continue to next ray
  % track if no match.
  track_type = rt0.hdmObj.track_type;
  trackTypeMismatched = strcmp(track_type,'SBR_PO') && ~includeSbr;
  trackTypeMismatched = trackTypeMismatched || ...
                        (strcmp(track_type,'UTD') && ~includeUtd);
  if trackTypeMismatched
    continue;
  end

  if filterSweepIdx
    % check this track's sweep angle index matches one in the idxAng list
    idx = find(fltrCfg.idxAng == rt0.hdmObj.sweep_angle_index);
    if isempty(idx)
      continue;  % no match, leave all draw flags as false for this ray track
    end
  end

  % track not being skipped due to track-level filters, proceed with two
  % more passes to update draw flags according to fltrCfg properties
  recurse_track(rbSrc,0,0,@set_draw_branch);
  recurse_track(rbSrc,0,0,@set_draw_flags);
end  % for itrack = 1:Ntrack

if ~alreadyFiltered
  bundle.hdmObj.min_fp_cumulative_dist = minFpDistBundle;
  bundle.hdmObj.max_cumulative_dist = maxDistBundle;

  if isPwSource
    % add the sweep angle index map
    %
    % The map gets populated during creation of the source_bounce, which only
    % occurs on the first pass of the ray bundle through ray_filters1.
    % On subsequent passes, the local map container will be empty, so we
    % don't want to replace the cached map with an empty one. That's why
    % we check if ray bundle has already been filtered.
    bundle.hdmObj.pwinc_map = sweepAngIdxMap;
  end
end
bundle.hdmObj.filter = filter_func_name;
bundle.hdmObj.filterCfg = fltrCfg;
end  % filter_rays1

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function [theta phi] = rvec2thetaphi(rvec)
% RVEC2THETAPHI generate spherical-coord angles from outward radial vector
%
% Input Params:
%  rvec (1x3 dbl) outward pointing radial vector, not assumed to be unit vec
%
% Returns:
%  theta (dbl) theta angle [rad]
%  phi   (dbl) phi angle [rad]
rlen = sqrt(dot(rvec,rvec));
if rlen == 0
  % this should not happen
  theta = nan;
  phi = nan;
else
  rvec = rvec/rlen;
  rho = sqrt(dot(rvec(1:2),rvec(1:2)));
  theta = atan2(rho,rvec(3));
  phi = atan2(rvec(2),rvec(1));
end
end  % rvec2thetaphi
