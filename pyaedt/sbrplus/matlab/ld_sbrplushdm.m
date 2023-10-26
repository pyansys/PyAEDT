function hdm = ld_sbrplushdm(fname,asStruct,showProg)
% LD_SBRPLUSHDM load an HDM-format export file from HFSS SBR+
%
% Files exported in HFSS SBR+ .hdm (Heterogeneous Data Message) format are
% binary messages (i.e., data structure serializations) whose content doesn't
% necessarily conform to a data table representation. For example, the HDM
% format is used to export SBR+ rays from AEDT. An HDM file begins with an
% ASCII header that describes both the format and content of the binary message
% that follows it, providing sufficient information to parse and deserialize
% the binary message.
%
% LD_SBRPLUSHDM parses the message schema in the header and then uses this
% to read and deserialize the binary message. It returns the deserialization
% as a MATLAB struct with field names determined from the header's schema
% block. Data structures tagged as optional in the binary message are
% represented as empty struct fields where applicable.
%
% PREREQUISITE: a Python installation compatible with the installed MATLAB
% version. Invoke the MATLAB pyenv command to verify that a supported version
% of Python is available; if pyenv returns an empty Version field, then
% a supported version of Python could not be found by MATLAB. Consult MATLAB
% help on Python to learn more about the supported Python versions and how
% to install them.
%
% DEPRECATED BEHAVIOR: the option asStruct == true is no longer supported.
%
% Invoking it will cause MATLAB to throw an error() exception. It is
% nonetheless retained as the DEFAULT setting for asStruct to maintain function
% interface backward compatibility and elevate the modified behavior as an
% error. Existing toolchains using asStruct == true, whether explicitly or by
% default, must be modified to work with a returned hdm struct whose top-level
% message is now an HdmObject handle object effectively referencing struct
% fields rather than the struct fields themselves. The legacy structure
% representation made the returned hdm struct and subsets of its descendent
% tree extremely inefficient to pass between MATLAB functions since MATLAB
% function arguments are always passed by value and cause the entire argument
% contents to be copied. It is more efficient to pass large objects between
% MATLAB functions using MATLAB handles (i.e., using MATLAB classes like
% HdmObject that inherit from the MATLAB 'handle' class). If your toolchain
% relies on the legacy struct representation, you may consult the provided
% filter_rays1.m, draw_rays1.m, and HdmObject.m script files for examples of
% how to work with the HdmObject handle representation.
%
% Input Params:
%   fname (str) full path name of .hdm file, DEFAULT = [] = select
%               interactively from file dialog
%
%   asStruct (lgc) true  = return top level message as MATLAB struct fields,
%                          sub-messages will still contain HdmObjects (DEFAULT)
%                          DEPRECATED, this option no longer supported and will
%                          trigger a MATLAB error()
%                  false = return as HdmObject handle object placed within
%                          return value struct, facilitates efficient passing
%                          to other functions, ALWAYS set asStruct to false
%
%   showProg (lgc) true   = show file load progress in progress bar for files
%                           over 1 Mb in size (DEFAULT)
%                  false  = load quietly without progress bar, fastest
%            (str) 'text' = show progress as text line in console window
%
% Returns:
%  hdm (struct) deserialization of the binary message, the struct and HdmObject
%               field names are determined from the message schema in the HDM
%               ASCII file header
%   .hdm (HdmObject) top-level handle object for holding imported HDM message,
%                    this struct field only returned when asStruct is false
%
%   .dirpath   (str) directory path of loaded HDM file
%   .filename  (str) file name of loaded HDM file, does not include dir. path
%   .ldtime    (dbl) time to load HDM file [sec]
%
% hdm = LD_SBRPLUSHDM([fname][,asStruct][,showProg])
%
% COPYRIGHT ANSYS, Inc. ALL RIGHTS RESERVED.

  if ~exist('fname','var') fname = ''; end

  if ~exist('asStruct','var') asStruct = []; end
  if isempty(asStruct) asStruct = true; end

  if ~exist('showProg','var') showProg = true; end

  if asStruct
    error('ld_sbrplushdm:deprecatedOption',...
          'Setting asStruct to true is no longer supported.');
  end

  if isempty(fname)
    % file name not provided, obtain interactively from file dialog
    [fname pathname] = uigetfile('*.hdm','Open HFSS SBR+ HDM file');
    if fname
      fname = fullfile(pathname,fname);
    else
      error('ld_sbrplushdm:noFileSpecified','No file specified to load');
    end
  end

  % create and start timer for file load process
  stopWatch = StopWatch();
  stopWatch.start();

  [fid, errmsg] = fopen(fname, 'r');
  if fid < 0
    delete(stopWatch);
    error(errmsg);
  end

  % parse ASCII file header to determine format of binary HDM data block
  %
  % All info needed to parse the binary HDM data block is contained in the
  % header as a Python dictionary.
  grammar = struct(); 
  grammar.basic_types = ["int", "float", "enum", "flag", "complex"];
  try
    grammar.header = parseHeader(fid);
  catch exception
    fclose(fid);
    delete(stopWatch);
    rethrow(exception)
  end
  fn = fieldnames(grammar.header.types);
  grammar.flags_defs = containers.Map;
  grammar.enum_defs = containers.Map;
  for ifn = 1:numel(fn)
    iobj = grammar.header.types.(fn{ifn});
    itype = iobj.type;
    if strcmp(itype, 'enum')
      keys = double(iobj.start) + (0:numel(iobj.values)-1);
      grammar.enum_defs(fn{ifn}) = containers.Map(keys, iobj.values);
    elseif strcmp(itype, 'flag')
      grammar.flags_defs(fn{ifn}) = fieldnames(iobj.values);
    end
  end

  % read the entire binary HDM data block according to format information
  % gathered in the ASCII header
  try
    progPeriod = 0.5;  % progress report every 0.5 sec
    minFileSize_Mb = 2;  % minimum file size to show progress
    start_prog_monitor(showProg,fname,progPeriod,minFileSize_Mb*1000000);
    if asStruct
      % force returned object to be a struct rather than single HdmObject,
      % avoids extra layer of indirection at top level, still uses HdmObject
      % handle objects at all sub levels where applicable
      how_many = 0;
      hdm = parse(fid, grammar, grammar.header.message.type, how_many);

    else
      % return value struct will contain a single HdmObject handle object with
      % the top-level message, which is more efficient to pass around for
      % post-proc
      %
      % Need to tuck into <return_val>.hdm so that file path info can be
      % appended later
      how_many = 1;
      hdm.hdm = parse(fid, grammar, grammar.header.message.type, how_many);
    end
  
  catch exception
    stop_prog_monitor();
    fclose(fid);
    delete(stopWatch);
    rethrow(exception)
  end
  stop_prog_monitor();
  fclose(fid);
  stopWatch.stop();

  % append HDM file dir path and root name to returned data structure
  [dirname, frootnm, ext] = fileparts(fname);
  frootnm = [frootnm, ext];
  hdm.dirpath = dirname;
  hdm.filename = frootnm;
  hdm.ldtime = stopWatch.elapsedTime();
  delete(stopWatch);
end  % ld_sbrplushdm

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function header = parseHeader(fid)
% parses the header of an already opened hdm export file
%
% removes content lines starting with '#', parses the header as a
% Python dictionary, and converts it to Matlab format 
% 
% Input Params:
%   fid       (int) file ID from fopen function referring to an hdm file
% 
% Returns:
%   header (struct) content of the hdm header in struct format

  tline = fgetl(fid);
  lineCounter = 1;
  out = '';
  while ischar(tline)
    if contains(tline, '#')
      out = string([out, extractBefore(tline,'#')]);
    else
      out = string([out, tline]);
    end
    if strcmp(tline, '#header end')
      break;
    end
    % Read next line
    tline = fgetl(fid);
    lineCounter = lineCounter + 1;
  end
  header = pydict2struct_recursive(py.eval(strjoin(out), py.dict()));
end  % parseHeader

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function matlab_data = pydict2struct_recursive(python_data)
% converts a python data structure to a matlab one. Called recursively
% for dictionaries and list/tuples.
%        dict -> struct
%         str -> char
%         int -> int64
%       float -> double
%   otherwise -> cell array
% 
% Input Params:
%   python_data   (any) python data format
% 
% Returns:
%   matlab_data   (any) converted python data 
  if isequal(python_data, py.dict)
    matlab_data = struct(python_data);
    fields = fieldnames(matlab_data);
    for ifld = 1:length(fields)
      matlab_data.(fields{ifld}) = ...
        pydict2struct_recursive(matlab_data.(fields{ifld}));
    end
    if isfield(matlab_data, 'field_names') && ~isfield(matlab_data, 'optional')
      matlab_data.optional = [];
    end
  elseif isequal(python_data, py.str)
    matlab_data = char(python_data);
  elseif isequal(python_data, py.int)
    matlab_data = python_data.int64;
  elseif isequal(python_data, py.float)
    matlab_data = double(python_data);
  else
    matlab_data = cell(python_data);
    for ik=1:numel(matlab_data)
      matlab_data{ik} = pydict2struct_recursive(matlab_data{ik});
    end
  end
end  % pydict2struct_recursive

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function content = parse(fid, grammar, typename, how_many)
% PARSE base parse factory for binary data
%
% Must call after the header has been parsed already.
% 
% Input Params:
%   fid      (int) file ID from fopen function referring to an hdm file
%   grammar  (struct) data structure describing how to parse the message,
%                     see parseHeader      
%   typename (str) name of a type to parse, must be represented in grammar
%   how_many (int) number of objects or basic types to parse, ignored when
%                  type associated with typename is vector or list, set to
%                  zero (0) instead of (1) when parsing a single object
%                  to force it to come back as a struct rather than an
%                  HdmObject containing the struct
%
% Returns:
%   content  (HdmObject/array/basic type) content extracted from the binary
%            file. It can be a single HdmObject, an array (vector/list) or a
%            POD type. Lists of objects of the same type are returned as an
%            array of structs (not HdmObjects), though its struct fields can
%            have singleton HdmObjects.

  type_struct = grammar.header.types.(typename);
  type = type_struct.type;
  %how_many0 = max(how_many,1);
  if strcmp(type, 'object')
    %if (how_many == 1)
    %  content = HdmObject(parse_object(fid, grammar, typename, 1));
    %else
    %  content = parse_object(fid, grammar, typename, how_many0);
    %end
    content = parse_object(fid, grammar, typename, how_many);

  elseif any(strcmp(type, {'vector', 'list'}))
    basetype = type_struct.base;
    size = type_struct.size;
    content = parse_array(fid, grammar, type, basetype, size);

  else
    %content = parse_basic(fid, grammar, typename, how_many0);
    content = parse_basic(fid, grammar, typename, how_many);
  end
end  % parse

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function content = parse_object(fid, grammar, typename, how_many)
% parse method to parse an object from binary data. Given an object
% typename, recovers its layout from the grammar, and parses all the object
% fields. If an object field is optional and not parsed, it is inserted in
% the struct as [].
% 
% Input Params:
%   fid      (int) file ID from fopen function referring to an hdm file
%   grammar  (struct) data structure describing how to parse the message,
%                     see parseHeader      
%   typename (str) name of a type to parse, must be represented in grammar
%   how_many (int) number of object instances to parse
%
% Returns:
%   content  (struct) object content extracted from the binary file

  if how_many == 0
    content = [];
    return;
  end

  grammartypes = grammar.header.types;
  layout_description = grammartypes.(typename).layout;
  %content(how_many,1) = struct;
  content(how_many,1) = HdmObject;  % vector of HdmObjects
  for ic = 1:how_many
    hdm0 = content(ic);

    for il=1:numel(layout_description)
      % looping items in the layout
      layout = layout_description{il};
      layout_type = layout.type;

      skip_field = false;
      if ~isempty(layout.optional)
        % Existence of this layout item depends on the state of a boolean flag
        % or enum appearing earlier in the layout. If the flag is false or the
        % enum value does not match, DO NOT read and parse the field(s) of this
        % layout item, as no content has been recorded for it, and the next
        % bytes in the binary stream are for the next layout item. 
        optional_cond = layout.optional;
        %cond1 = content(ic).(optional_cond{1});
        cond1 = hdm0.hdmObj.(optional_cond{1});
        if isstruct(cond1)
          % optional field(s) depend(s) upon an earlier flag
          %skip_field = ~content(ic).(optional_cond{1}).(optional_cond{2});
          skip_field = ~hdm0.hdmObj.(optional_cond{1}).(optional_cond{2});
        else
          % optional field(s) depend(s) upon an earlier enum
          skip_field = ~strcmp(cond1, optional_cond{2});
        end
      end

      fld_names = layout.field_names;
      if ~iscell(fld_names)
        fld_names = {fld_names};
      end

      for ifn = 1:numel(fld_names)
        % looping through fields of this layout item
        fn = fld_names{ifn};
        if skip_field
          % optional field not present - do not parse and set to empty
          %content(ic).(fn) = [];
          hdm0.hdmObj.(fn) = [];

        elseif any(strcmp(layout_type, {'vector', 'list'}))
          size = layout.size;
          if ischar(size)
            % size of vector or list specified by earlier field in object
            % layout - evaluate it
            %size = content(ic).(size);
            size = hdm0.hdmObj.(size);
          end
          %content(ic).(fn) = parse_array(fid, grammar, layout_type, ...
          %                               layout.base, size);
          hdm0.hdmObj.(fn) = parse_array(fid, grammar, layout_type, ...
                                         layout.base, size);
        
        else
          % Check if the message refers to an array type
          msgtype = grammartypes.(layout_type);
          if strcmp(msgtype.type, 'vector') || strcmp(msgtype.type, 'list')
            size = msgtype.size;
            if ischar(size)
              %size = content(ic).(size);
              size = hdm0.hdmObj.(size);
            end
            %content(ic).(fn) = parse_array(fid, grammar, msgtype.type, ...
            %                               msgtype.base, size);
            hdm0.hdmObj.(fn) = parse_array(fid, grammar, msgtype.type, ...
                                           msgtype.base, size);
          
          else
            if strcmp(msgtype.type, 'flag')
              % layout item is a flag type, requires special handling to
              % extract individual bits and assign each to different sub-field
              % name
              flag_content = parse(fid, grammar, layout_type, 1);
              flagvals = grammar.flags_defs(layout_type);
              bits = logical(bitget(flag_content,1:numel(flagvals)));
              %content(ic).(fn) = cell2struct(num2cell(bits), flagvals, 2);
              hdm0.hdmObj.(fn) = cell2struct(num2cell(bits), flagvals, 2);
            
            else
              %content(ic).(fn) = parse(fid, grammar, layout.type, 1);
              hdm0.hdmObj.(fn) = parse(fid, grammar, layout.type, 1);
            end
          end
        end
      end  % fields loop

    end  % layout loop
  end  % object loop (how_many)
end  % prase_object

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function content = parse_array(fid, grammar, typename, base, size)
% parse method to parse a vector or list (repeated message) from binary data.
% 
% Input Params:
%   fid      (int) file ID from fopen function referring to an hdm file
%   grammar  (struct) data structure describing how to parse the message,
%                     see parseHeader      
%   typename (str) vector or list.
%   base     (str) underlying type for the repeated message
%   size     (str) number of repeated messages
%
% Returns:
%   content  (struct) array content extracted from the binary file

  if strcmp(typename, 'vector')
    % returns a row array and must have a basic type as its
    % underlying type
    content = transpose(parse_basic(fid, grammar, base, size));

  else % list
    % returns a matrix if the base type is a vector, a column vector
    % if the base type is a basic type or struct
    if strcmp(grammar.header.types.(base).type, 'vector')
        % each vector instance corresponds to a row
        base_vector_struct = grammar.header.types.(base);
        base_type = base_vector_struct.base;
        nrows = base_vector_struct.size;
        total_size = size*nrows;
        content = parse_basic(fid, grammar, base_type, total_size);
        content = transpose(reshape(content, [nrows, size]));

    elseif any(strcmp(grammar.basic_types, grammar.header.types.(base).type))
        content = transpose(parse_basic(fid, grammar,  base, size));

    else
        % reading a list of objects of same type
        %if (size > 1)
        %  content = parse_object(fid,grammar,base,size);
        %elseif (size == 0)
        %  content = [];
        %else
        %  content = HdmObject(parse_object(fid,grammar,base,size));
        %end
        content = parse_object(fid,grammar,base,size);
    end
  end
end  % parse_array

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function content = parse_basic(fid, grammar, typename, how_many)
% parse method to parse a basic type (int, float, enum, flag, complex)
% 
% Input Params:
%   fid      (int) file ID from fopen function referring to an hdm file
%   grammar  (struct) data structure describing how to parse the message,
%                     see parseHeader      
%   typename (str) int, enum, flag, float or complex.
%   how_many (int) number of basic types to read from binary data
%
% Returns:
%   content  (struct) array content extracted from the binary file

  global LD_PROG_MON

  format = grammar.header.types.(typename);
  if any(strcmp(format.type, {'int', 'enum', 'flag'}))
    if format.size == 4
      readas = '*int32';
    elseif format.size == 1 && strcmp(format.type, 'flag')
      readas = '*uint8';
    elseif format.size == 1
      readas = '*int8';
    end
    res = fread(fid, how_many, readas);
    if strcmp(format.type, 'enum')
      enum = grammar.enum_defs(typename);
      res = enum(res);
    end

  elseif strcmp(format.type, 'float')
    if format.size == 8
      readas = 'double';
    elseif format.size == 4
      readas = '*float';
    end
    res = fread(fid, how_many, readas);

  elseif strcmp(format.type, 'complex')
    how_many = how_many*2;
    if format.size == 16
      readas = 'double';
    elseif format.size == 8
      readas = '*float';
    end
    res = fread(fid, how_many, readas);
    res = complex(res(1:2:end), res(2:2:end));
  end
  content = res;

  if LD_PROG_MON.showProg
    % update info needed to determine file load progress, computed as
    %   prog_numer/prog_denom = bytes_read/file_size_in_bytes
    LD_PROG_MON.prog_numer = ftell(fid);
  end
end  % parse_basic

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function start_prog_monitor(showProg,fname,progPeriod,minFileSize)
% launch the load progress monitor
%
% Creates a timer that calls a callback function at regular time intervals
% to report file load progress. Supports either a graphical progress bar
% or text output to console.
%
% Input Params:
%  showProg (lgc)  true  = show file load progress in progress bar
%                 false  = load quietly without progress bar
%           (str) 'text' = show progress as text line in console window
%
%  fname    (str) full path name of file being loaded, used to determine file
%                 size in bytes, the denominator in fraction complete
%
%  progPeriod  (dbl) time interval between progress reports [sec]
%  minFileSize (int) minimum file size to activate progress monitor [bytes],
%                    files smaller than this will load quietly

global LD_PROG_MON

LD_PROG_MON.showProg = false;
LD_PROG_MON.doProgBar = false;

if ischar(showProg)
  if strcmp(showProg,'text')
    % show file load progress as text to console window
    LD_PROG_MON.showProg = true;
    LD_PROG_MON.doProgBar = false;
  else
    LD_PROG_MON.showProg = false;
    error('ld_sbrplushdm:badInput', ...
          'Unrecognized string input to showProg argument: %s',showProg);
  end
  
elseif islogical(showProg)
  % show progress in graphical progress bar
  LD_PROG_MON.showProg = showProg;
  LD_PROG_MON.doProgBar = true;
end 

if ~LD_PROG_MON.showProg
  % no progress monitoring requested
  return;
end

finfo = dir(fname);
LD_PROG_MON.prog_denom = finfo.bytes;
LD_PROG_MON.prog_numer = 0;
LD_PROG_MON.wbar = 0;  % graphical progress (wait) bar
LD_PROG_MON.oldTextLen = 0;  % used to precisely erase earlier text
                             % progress reports

if finfo.bytes < minFileSize
  % file too small to be worth monitoring load progress
  LD_PROG_MON.showProg = false;
  return;
end

if LD_PROG_MON.doProgBar
  % set up graphical progress bar
  %
  % Underscores in file name will trigger sub-scripting unless preceded by
  % backslash to be taken as literal and not a control code.
  frootnm = strrep(finfo.name,'_','\_');
  LD_PROG_MON.wbar = waitbar(0,['Loading HDM File: ' frootnm]);
end

% create MATLAB timer object to call the progress monitor callback function
% at regular time intervals
period = 0.5;  % update every 0.5 sec
LD_PROG_MON.tmr = timer('TimerFcn',{@prog_monitor_cb},'Period',progPeriod,...
                        'ExecutionMode','fixedRate');
start(LD_PROG_MON.tmr);

end  % start_prog_monitor

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function prog_monitor_cb(obj,event)
% callback function to update progress report to progress bar or console text
%
% See MATLAB timer documentation regarding arguments of callback function.
%
% Input Params:
%  obj    (Timer) timer object that invoked this callback, ignored
%  event (struct) timer event properties, ignored
global LD_PROG_MON

progress = LD_PROG_MON.prog_numer/LD_PROG_MON.prog_denom;

if LD_PROG_MON.doProgBar
  % update graphical progress bar
  waitbar(progress,LD_PROG_MON.wbar);

else
  % update text report of progress
  if LD_PROG_MON.oldTextLen > 0
    % erase old progress report from MATLAB console
    fprintf(repmat('\b',1,LD_PROG_MON.oldTextLen));
  end
  msg = sprintf('Load Completion: %0.1f%%',progress*100);
  LD_PROG_MON.oldTextLen = numel(msg);
  fprintf('%s',msg);
end
end  % prog_monitor_cb

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
function stop_prog_monitor()
% stop and shutdown the file load progress monitor

global LD_PROG_MON

if ~LD_PROG_MON.showProg
  return;
end

stop(LD_PROG_MON.tmr);
delete(LD_PROG_MON.tmr);

if LD_PROG_MON.doProgBar
  % close graphical progress (wait) bar
  close(LD_PROG_MON.wbar);
else
  % erase residual progress text that was sent to console
  if LD_PROG_MON.oldTextLen > 0
    fprintf(repmat('\b',1,LD_PROG_MON.oldTextLen));
  end
end
end  % stop_prog_monitor
